#!/usr/bin/env python3
"""
Image Combiner GUI - Drag and drop interface for combining two images

Required modules to install:
   python -m pip install pillow customtkinter tkinterdnd2

Python version: 3.10.11

Features:
- Drag and drop images into drop zones (supports JPG, JPEG, PNG, WEBP)
- Auto-generate output filename from FIRST input file name + "_c.webp"
- Update individual images by dragging new file to the same zone
- Preview thumbnails of selected images
- Click generate to combine images
- Output saved to 'output' folder
- NO WHITE SPACES - Images are scaled to match dimensions perfectly
- Auto-numbering to prevent overwriting existing files
- EXIF orientation handling - fixes rotated photos from cameras/phones
- Subtle black border between images for better distinction
"""

import os
import sys
import math
import threading
import re
import warnings
from pathlib import Path
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

# Suppress PIL decompression bomb warning for large images
warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)

# Set CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Maximum image dimensions (to prevent memory issues)
MAX_IMAGE_PIXELS = 100_000_000  # 100 megapixels
MAX_OUTPUT_DIMENSION = 10000    # Max width or height in pixels

def get_script_folder():
    """Get the folder where this script is located."""
    return Path(__file__).parent.absolute()

def ensure_output_folder():
    """Create output folder if it doesn't exist."""
    script_folder = get_script_folder()
    output_folder = script_folder / "output"
    output_folder.mkdir(exist_ok=True)
    
    # Check if folder is writable
    if not os.access(output_folder, os.W_OK):
        raise PermissionError(f"Output folder is not writable: {output_folder}")
    
    return output_folder

def validate_image_format(file_path):
    """Validate that the image is either JPG, JPEG, PNG, or WEBP format."""
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if not file_ext in valid_extensions:
        raise ValueError(f"Invalid file format. Only JPG/JPEG/PNG/WEBP are supported. Got: {file_ext}")
    
    return True

def apply_exif_orientation(img):
    """Apply EXIF orientation to image (fixes rotated photos from cameras/phones)"""
    try:
        # Get EXIF data
        exif = img._getexif()
        if exif:
            # EXIF orientation tag is 274
            orientation_key = 274
            if orientation_key in exif:
                orientation = exif[orientation_key]
                
                # Store original dimensions for logging
                original_size = img.size
                
                # Apply rotation based on orientation value
                if orientation == 2:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 4:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 6:
                    img = img.rotate(-90, expand=True)
                elif orientation == 7:
                    img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
                
                # If dimensions changed, log it (useful for debugging)
                if original_size != img.size:
                    print(f"  EXIF: Rotated image from {original_size[0]}x{original_size[1]} to {img.size[0]}x{img.size[1]}")
                    
    except (AttributeError, KeyError, TypeError, IndexError, ValueError):
        # No EXIF data or error reading it - silently ignore
        pass
    
    return img

def validate_image_size(img, file_path):
    """Validate image size to prevent memory issues."""
    pixels = img.width * img.height
    
    if pixels > MAX_IMAGE_PIXELS:
        raise MemoryError(f"Image too large: {img.width}×{img.height} ({pixels:,} pixels). "
                         f"Maximum allowed: {MAX_IMAGE_PIXELS:,} pixels")
    
    if img.width > MAX_OUTPUT_DIMENSION or img.height > MAX_OUTPUT_DIMENSION:
        raise ValueError(f"Image dimensions too large: {img.width}×{img.height}. "
                        f"Maximum allowed: {MAX_OUTPUT_DIMENSION} pixels per side")
    
    return True

def get_image_orientation(width, height):
    """Determine if image is portrait or landscape."""
    if height > width:
        return "portrait"
    else:
        return "landscape"

def get_resolution_pixels(img):
    """Calculate total pixels of an image."""
    return img.width * img.height

def check_aspect_ratio_warning(img1, img2):
    """Check if aspect ratios are extremely different and return warning message."""
    ratio1 = img1.width / img1.height
    ratio2 = img2.width / img2.height
    ratio_diff = abs(ratio1 - ratio2)
    
    if ratio_diff > 2.0:
        return "⚠️ Warning: Images have very different aspect ratios. Result may look uneven."
    elif ratio_diff > 1.0:
        return "⚠️ Note: Images have different aspect ratios."
    return None

def calculate_matched_dimensions(img1, img2, layout_mode, border_width):
    """
    Calculate dimensions to make both images match perfectly with no white space.
    Scales both images to the LOWER dimension to avoid upscaling/blurriness.
    Includes border spacing in calculations.
    """
    if layout_mode == "horizontal":
        # Side by side - match heights
        target_height = min(img1.height, img2.height)
        
        # Calculate scale factors
        scale1 = target_height / img1.height
        scale2 = target_height / img2.height
        
        # Calculate new dimensions
        new_width1 = int(img1.width * scale1)
        new_height1 = target_height
        new_width2 = int(img2.width * scale2)
        new_height2 = target_height
        
        # Output dimensions with border
        output_width = new_width1 + border_width + new_width2
        output_height = target_height
        
        scale_factor = min(scale1, scale2)  # For reporting
        
    else:  # vertical layout
        # Stacked - match widths
        target_width = min(img1.width, img2.width)
        
        # Calculate scale factors
        scale1 = target_width / img1.width
        scale2 = target_width / img2.width
        
        # Calculate new dimensions
        new_width1 = target_width
        new_height1 = int(img1.height * scale1)
        new_width2 = target_width
        new_height2 = int(img2.height * scale2)
        
        # Output dimensions with border
        output_width = target_width
        output_height = new_height1 + border_width + new_height2
        
        scale_factor = min(scale1, scale2)  # For reporting
    
    return {
        'output_width': output_width,
        'output_height': output_height,
        'img1_new_width': new_width1,
        'img1_new_height': new_height1,
        'img2_new_width': new_width2,
        'img2_new_height': new_height2,
        'scale_factor': scale_factor
    }

def convert_to_rgb(img):
    """Convert image to RGB, handling PNG transparency."""
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create white background for transparency
        if img.mode == 'P':
            img = img.convert('RGBA')
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        return background
    elif img.mode != 'RGB':
        return img.convert('RGB')
    return img

def combine_images_gui(img1_path, img2_path, output_filename, border_width=2, border_color=(0, 0, 0), progress_callback=None):
    """Main function to combine two images with NO white space and a subtle border."""
    script_folder = get_script_folder()
    output_folder = ensure_output_folder()
    output_path = output_folder / output_filename
    
    try:
        if progress_callback:
            progress_callback("Validating image formats...", 10)
        
        validate_image_format(img1_path)
        validate_image_format(img2_path)
        
        if progress_callback:
            progress_callback("Loading images...", 20)
        
        # Handle absolute or relative paths
        img1_full_path = Path(img1_path) if os.path.isabs(img1_path) else script_folder / img1_path
        img2_full_path = Path(img2_path) if os.path.isabs(img2_path) else script_folder / img2_path
        
        if not img1_full_path.exists():
            raise FileNotFoundError(f"First image not found: {img1_path}")
        if not img2_full_path.exists():
            raise FileNotFoundError(f"Second image not found: {img2_path}")
        
        # Open images with increased limit for large files
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        img1_original = Image.open(img1_full_path)
        img2_original = Image.open(img2_full_path)
        
        # Apply EXIF orientation to fix rotated photos
        img1_original = apply_exif_orientation(img1_original)
        img2_original = apply_exif_orientation(img2_original)
        
        # Validate image sizes
        validate_image_size(img1_original, img1_path)
        validate_image_size(img2_original, img2_path)
        
        # Convert to RGB (handles PNG transparency)
        img1_original = convert_to_rgb(img1_original)
        img2_original = convert_to_rgb(img2_original)
        
        if progress_callback:
            progress_callback("Analyzing orientations...", 30)
        
        orientation1 = get_image_orientation(img1_original.width, img1_original.height)
        orientation2 = get_image_orientation(img2_original.width, img2_original.height)
        
        # Determine layout: both portrait = side by side, else stacked
        if orientation1 == "portrait" and orientation2 == "portrait":
            layout_mode = "horizontal"
        else:
            layout_mode = "vertical"
        
        # Check aspect ratio warning
        aspect_warning = check_aspect_ratio_warning(img1_original, img2_original)
        if aspect_warning and progress_callback:
            progress_callback(aspect_warning, 35)
        
        if progress_callback:
            progress_callback("Calculating matched dimensions...", 50)
        
        # Calculate dimensions to match perfectly (no white space)
        dims = calculate_matched_dimensions(img1_original, img2_original, layout_mode, border_width)
        
        if progress_callback:
            progress_callback(f"Scaling images (factor: {dims['scale_factor']:.3f}x)...", 60)
        
        # Scale both images to matched dimensions
        img1_scaled = img1_original.resize(
            (dims['img1_new_width'], dims['img1_new_height']), 
            Image.Resampling.LANCZOS
        )
        img2_scaled = img2_original.resize(
            (dims['img2_new_width'], dims['img2_new_height']), 
            Image.Resampling.LANCZOS
        )
        
        if progress_callback:
            progress_callback("Creating combined image with border...", 70)
        
        # Create combined image with border
        if layout_mode == "horizontal":
            # Create new image with combined width including border
            combined = Image.new('RGB', (dims['output_width'], dims['output_height']), border_color)
            
            # Paste images side by side with border
            combined.paste(img1_scaled, (0, 0))
            combined.paste(img2_scaled, (dims['img1_new_width'] + border_width, 0))
        else:
            # Create new image with combined height including border
            combined = Image.new('RGB', (dims['output_width'], dims['output_height']), border_color)
            
            # Paste images stacked with border
            combined.paste(img1_scaled, (0, 0))
            combined.paste(img2_scaled, (0, dims['img1_new_height'] + border_width))
        
        if progress_callback:
            progress_callback("Saving as WEBP...", 90)
        
        # Save as WEBP with normal compression
        combined.save(output_path, 'WEBP', quality=85, method=4)
        
        if progress_callback:
            progress_callback("Complete!", 100)
        
        return True, f"Success! Output saved to: {output_path}", output_path
        
    except MemoryError as e:
        return False, f"Memory Error: {str(e)}", None
    except PermissionError as e:
        return False, f"Permission Error: {str(e)}", None
    except FileNotFoundError as e:
        return False, f"File Error: {str(e)}", None
    except ValueError as e:
        return False, f"Value Error: {str(e)}", None
    except Exception as e:
        # Don't catch KeyboardInterrupt or SystemExit
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        return False, f"Error: {str(e)}", None

class ImageCombinerGUI:
    def __init__(self):
        # Create the main window with TkinterDnD support
        self.window = TkinterDnD.Tk()
        self.window.title("Image Combiner - Drag & Drop")
        self.window.geometry("950x750")
        self.window.configure(bg="#1a1a1a")
        
        # Store image paths
        self.image1_path = None
        self.image2_path = None
        
        # Border settings (instance variables, not globals)
        self.border_width = 2
        self.border_color = (0, 0, 0)  # RGB tuple
        self.border_color_name = "Black"
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self.window, 
            text="🖼️ Image Combiner", 
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Instructions
        instructions = ctk.CTkLabel(
            self.window,
            text="Drag and drop images into the zones below\nFirst image on left, second on right\n✨ No white spaces - images will be scaled to match perfectly\n🎨 Subtle black border between images for distinction",
            font=ctk.CTkFont(size=14)
        )
        instructions.pack(pady=10)
        
        # Main frame for images
        images_frame = ctk.CTkFrame(self.window)
        images_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Create left and right frames
        self.left_frame = ctk.CTkFrame(images_frame, width=380, height=380, fg_color="#2b2b2b")
        self.left_frame.pack(side="left", padx=20, pady=20, fill="both", expand=True)
        
        self.right_frame = ctk.CTkFrame(images_frame, width=380, height=380, fg_color="#2b2b2b")
        self.right_frame.pack(side="right", padx=20, pady=20, fill="both", expand=True)
        
        # Setup drop zones
        self.setup_drop_zone(self.left_frame, 1)
        self.setup_drop_zone(self.right_frame, 2)
        
        # Configure drag and drop for the frames
        self.left_frame.drop_target_register(DND_FILES)
        self.right_frame.drop_target_register(DND_FILES)
        self.left_frame.dnd_bind('<<Drop>>', lambda e: self.on_drop(e, 1))
        self.right_frame.dnd_bind('<<Drop>>', lambda e: self.on_drop(e, 2))
        
        # Allow clicking to browse
        self.left_frame.bind("<Button-1>", lambda e: self.select_file(1))
        self.right_frame.bind("<Button-1>", lambda e: self.select_file(2))
        
        # Info frame
        info_frame = ctk.CTkFrame(self.window)
        info_frame.pack(pady=10, padx=20, fill="x")
        
        self.info_label = ctk.CTkLabel(
            info_frame, 
            text="📌 Status: Waiting for images...",
            font=ctk.CTkFont(size=12)
        )
        self.info_label.pack(pady=5)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.window, width=600, height=15)
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)
        
        # Generate button
        self.generate_button = ctk.CTkButton(
            self.window,
            text="✨ GENERATE COMBINED IMAGE ✨",
            command=self.generate_combined,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            state="disabled",
            fg_color="#2e7d32",
            hover_color="#1b5e20"
        )
        self.generate_button.pack(pady=20)
        
        # Output frame
        output_frame = ctk.CTkFrame(self.window)
        output_frame.pack(pady=10, padx=20, fill="x")
        
        self.output_label = ctk.CTkLabel(
            output_frame,
            text="📁 Output will be saved in 'output' folder as [first_image_name]_c.webp",
            font=ctk.CTkFont(size=12)
        )
        self.output_label.pack(pady=5)
        
        # Border settings frame
        border_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        border_frame.pack(pady=5)
        
        border_label = ctk.CTkLabel(
            border_frame,
            text="Border width:",
            font=ctk.CTkFont(size=11)
        )
        border_label.pack(side="left", padx=5)
        
        # Fixed: Use StringVar for OptionMenu (not IntVar)
        self.border_width_var = ctk.StringVar(value="2")
        border_menu = ctk.CTkOptionMenu(
            border_frame,
            values=["0", "1", "2", "3", "4", "5", "6", "8", "10"],
            variable=self.border_width_var,
            command=self.update_border_width,
            width=80
        )
        border_menu.pack(side="left", padx=5)
        
        border_color_label = ctk.CTkLabel(
            border_frame,
            text="Border color:",
            font=ctk.CTkFont(size=11)
        )
        border_color_label.pack(side="left", padx=20)
        
        self.border_color_var = ctk.StringVar(value="Black")
        color_menu = ctk.CTkOptionMenu(
            border_frame,
            values=["Black", "White", "Gray", "Dark Gray", "Custom..."],
            variable=self.border_color_var,
            command=self.update_border_color,
            width=120
        )
        color_menu.pack(side="left", padx=5)
        
        # Hint for clicking
        hint_label = ctk.CTkLabel(
            self.window,
            text="💡 Tip: Click on drop zones to browse files | Drag & drop to replace | No white spaces! | Supports JPG, PNG, WEBP | Auto-rotates photos",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hint_label.pack(pady=5)
    
    def update_border_width(self, value):
        """Update the border width setting"""
        try:
            new_width = int(value)
            # Clamp to reasonable range
            if 0 <= new_width <= 50:
                self.border_width = new_width
                self.update_status(f"Border width set to {self.border_width} pixels", "blue")
            else:
                self.update_status(f"Border width {new_width} is out of range (0-50)", "red")
                # Reset to previous value in dropdown
                self.border_width_var.set(str(self.border_width))
        except ValueError:
            self.update_status(f"Invalid border width: {value}", "red")
    
    def update_border_color(self, value):
        """Update the border color setting"""
        color_map = {
            "Black": (0, 0, 0),
            "White": (255, 255, 255),
            "Gray": (128, 128, 128),
            "Dark Gray": (64, 64, 64)
        }
        
        if value in color_map:
            self.border_color = color_map[value]
            self.border_color_name = value
            self.update_status(f"Border color set to {value}", "blue")
        elif value == "Custom...":
            self.open_custom_color_dialog()
    
    def open_custom_color_dialog(self):
        """Open a simple dialog for custom RGB color input"""
        from tkinter import simpledialog, messagebox
        
        color_input = simpledialog.askstring(
            "Custom Color", 
            "Enter RGB values separated by commas (e.g., 128,0,255)\nRange: 0-255",
            parent=self.window
        )
        
        if color_input:
            try:
                # Remove any whitespace and split
                color_input = color_input.strip()
                parts = color_input.split(',')
                
                if len(parts) != 3:
                    messagebox.showerror("Error", "Please enter exactly 3 values separated by commas")
                    # Reset dropdown
                    self.border_color_var.set(self.border_color_name)
                    return
                
                r = int(parts[0].strip())
                g = int(parts[1].strip())
                b = int(parts[2].strip())
                
                # Validate range
                if all(0 <= v <= 255 for v in (r, g, b)):
                    self.border_color = (r, g, b)
                    self.border_color_name = f"Custom(RGB)"
                    self.update_status(f"Custom border color set to RGB({r},{g},{b})", "blue")
                else:
                    messagebox.showerror("Error", "RGB values must be between 0 and 255")
                    # Reset dropdown
                    self.border_color_var.set(self.border_color_name)
                    
            except ValueError:
                messagebox.showerror("Error", "Invalid input. Please use numbers separated by commas")
                # Reset dropdown
                self.border_color_var.set(self.border_color_name)
    
    def setup_drop_zone(self, frame, side):
        """Setup initial drop zone content"""
        for widget in frame.winfo_children():
            widget.destroy()
        
        drop_label = ctk.CTkLabel(
            frame, 
            text=f"📂 DROP IMAGE {side} HERE\n\nor click to browse\n\n.JPG .JPEG .PNG .WEBP",
            font=ctk.CTkFont(size=16),
            justify="center"
        )
        drop_label.pack(expand=True, fill="both", padx=10, pady=10)
        # No need to store reference as attribute
    
    def create_thumbnail(self, image_path, target_size=(350, 350)):
        """Create a thumbnail for preview with EXIF orientation applied"""
        try:
            img = Image.open(image_path)
            # Apply EXIF orientation to fix rotated photos in preview
            img = apply_exif_orientation(img)
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            return photo, img.size
        except Exception as e:
            print(f"Thumbnail error for {image_path}: {e}")
            return None, None
    
    def update_preview(self, frame, image_path, side):
        """Update preview image in the frame"""
        # Clear existing widgets
        for widget in frame.winfo_children():
            widget.destroy()
        
        if image_path:
            # Create thumbnail
            photo, original_size = self.create_thumbnail(image_path)
            if photo:
                # Preview image
                preview_label = ctk.CTkLabel(frame, image=photo, text="")
                preview_label.image = photo  # Keep reference
                preview_label.pack(pady=15)
                
                # Filename
                filename = os.path.basename(image_path)
                name_label = ctk.CTkLabel(
                    frame, 
                    text=filename, 
                    font=ctk.CTkFont(size=12, weight="bold"),
                    wraplength=340
                )
                name_label.pack(pady=5)
                
                # Dimensions
                dims_label = ctk.CTkLabel(
                    frame,
                    text=f"📐 {original_size[0]}×{original_size[1]} pixels",
                    font=ctk.CTkFont(size=11)
                )
                dims_label.pack(pady=2)
                
                # Replace instruction
                replace_label = ctk.CTkLabel(
                    frame,
                    text="↓ Drag new file here or click to replace ↓",
                    font=ctk.CTkFont(size=10),
                    text_color="#888888"
                )
                replace_label.pack(pady=10)
            else:
                error_label = ctk.CTkLabel(
                    frame, 
                    text="❌ Error loading image", 
                    font=ctk.CTkFont(size=14)
                )
                error_label.pack(expand=True)
        else:
            # Show drop zone again
            drop_label = ctk.CTkLabel(
                frame, 
                text=f"📂 DROP IMAGE {side} HERE\n\nor click to browse\n\n.JPG .JPEG .PNG .WEBP",
                font=ctk.CTkFont(size=16),
                justify="center"
            )
            drop_label.pack(expand=True, fill="both", padx=10, pady=10)
    
    def on_drop(self, event, side):
        """Handle drop for image slots"""
        file_path = event.data.strip('{}')
        
        if not file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            self.update_status(f"❌ Invalid format: {os.path.basename(file_path)}. Use JPG, JPEG, PNG, or WEBP", "red")
            return
        
        if side == 1:
            self.image1_path = file_path
            self.update_preview(self.left_frame, self.image1_path, 1)
            self.update_status(f"✅ Image 1 loaded: {os.path.basename(file_path)}", "green")
        else:
            self.image2_path = file_path
            self.update_preview(self.right_frame, self.image2_path, 2)
            self.update_status(f"✅ Image 2 loaded: {os.path.basename(file_path)}", "green")
        
        self.check_ready()
    
    def select_file(self, side):
        """Open file dialog to select image"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title=f"Select Image {side}",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.webp"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("WEBP files", "*.webp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            if side == 1:
                self.image1_path = file_path
                self.update_preview(self.left_frame, self.image1_path, 1)
                self.update_status(f"✅ Image 1 loaded: {os.path.basename(file_path)}", "green")
            else:
                self.image2_path = file_path
                self.update_preview(self.right_frame, self.image2_path, 2)
                self.update_status(f"✅ Image 2 loaded: {os.path.basename(file_path)}", "green")
            self.check_ready()
    
    def auto_generate_filename(self):
        """
        Create filename from FIRST input file name + "_c.webp"
        Example: if first image is "sunset.jpg", output will be "sunset_c.webp"
        Auto-numbers if file exists to prevent overwriting
        """
        if not self.image1_path:
            return "combined_output.webp"
        
        # Get base name without extension
        name1 = os.path.splitext(os.path.basename(self.image1_path))[0]
        
        # Clean filename (remove invalid characters)
        name1 = re.sub(r'[<>:"/\\|?*]', '_', name1)
        
        # Create output filename
        base_output_name = f"{name1}_c.webp"
        
        # Check if file exists and add number if needed
        try:
            output_folder = ensure_output_folder()
        except Exception:
            return base_output_name
        
        output_path = output_folder / base_output_name
        
        if not output_path.exists():
            return base_output_name
        
        # File exists, add number
        counter = 1
        while True:
            output_name = f"{name1}_c_{counter}.webp"
            output_path = output_folder / output_name
            if not output_path.exists():
                return output_name
            counter += 1
    
    def update_status(self, message, color="white"):
        """Update status message"""
        self.info_label.configure(text=f"📌 Status: {message}", text_color=color)
    
    def update_progress(self, message, progress):
        """Update progress bar and status"""
        # Always update progress bar for numeric progress
        if isinstance(progress, (int, float)) and 0 <= progress <= 100:
            self.progress_bar.set(progress / 100)
        
        # Update status message
        self.update_status(message)
        self.window.update_idletasks()
    
    def check_ready(self):
        """Check if both images are loaded and enable generate button"""
        if self.image1_path and self.image2_path:
            # Show what the output filename will be
            output_name = self.auto_generate_filename()
            self.output_label.configure(
                text=f"📁 Output will be: {output_name}",
                text_color="#4caf50"
            )
            self.generate_button.configure(state="normal")
            self.update_status("✅ Both images loaded - ready to generate!", "green")
        else:
            self.generate_button.configure(state="disabled")
            if not self.image1_path and not self.image2_path:
                self.output_label.configure(
                    text="📁 Output will be saved in 'output' folder as [first_image_name]_c.webp",
                    text_color="gray"
                )
    
    def generate_combined(self):
        """Generate the combined image"""
        if not self.image1_path or not self.image2_path:
            self.update_status("❌ Please load both images first!", "red")
            return
        
        # Auto-generate output filename
        output_filename = self.auto_generate_filename()
        
        # Disable button during processing
        self.generate_button.configure(state="disabled", text="⏳ PROCESSING...")
        self.update_status("Processing images...", "yellow")
        
        # Store current border settings for this operation
        current_border_width = self.border_width
        current_border_color = self.border_color
        
        # Run in separate thread to keep UI responsive
        def process():
            try:
                success, message, output_path = combine_images_gui(
                    self.image1_path, 
                    self.image2_path, 
                    output_filename,
                    current_border_width,
                    current_border_color,
                    self.update_progress
                )
                
                # Update UI in main thread
                self.window.after(0, lambda: self.on_process_complete(success, message, output_path))
            except Exception as e:
                # Handle any thread errors
                self.window.after(0, lambda: self.on_process_complete(False, f"Thread error: {str(e)}", None))
        
        thread = threading.Thread(target=process, daemon=False)  # Non-daemon for safe completion
        thread.start()
    
    def on_process_complete(self, success, message, output_path):
        """Handle completion of image processing"""
        if success:
            self.update_status(f"✅ SUCCESS! {message}", "green")
            self.output_label.configure(text=f"✅ Output saved: {output_path.name}", text_color="lightgreen")
            self.progress_bar.set(1.0)
            
            # Ask if user wants to open output folder
            from tkinter import messagebox
            if messagebox.askyesno("Complete", f"✨ Image combined successfully!\n\nOutput saved as:\n{output_path.name}\n\nOpen output folder?"):
                try:
                    output_folder = ensure_output_folder()
                    if sys.platform == "win32":
                        os.startfile(output_folder)
                    elif sys.platform == "darwin":  # macOS
                        import subprocess
                        subprocess.Popen(["open", output_folder])
                    else:  # Linux
                        import subprocess
                        subprocess.Popen(["xdg-open", output_folder])
                except Exception as e:
                    self.update_status(f"⚠️ Could not open folder: {e}", "yellow")
        else:
            self.update_status(f"❌ FAILED: {message}", "red")
            self.output_label.configure(text="❌ Generation failed. Check error message above.", text_color="red")
            self.progress_bar.set(0)
        
        # Re-enable button
        self.generate_button.configure(state="normal", text="✨ GENERATE COMBINED IMAGE ✨")
    
    def run(self):
        """Start the GUI application"""
        self.window.mainloop()

def main():
    """Main function to start the GUI"""
    print("\n" + "="*60)
    print("🖼️ IMAGE COMBINER GUI - Drag and Drop Interface")
    print("="*60)
    print("\nStarting GUI application...")
    print("Features:")
    print("  • Drag and drop images into the zones")
    print("  • Click zones to browse for files")
    print("  • Output filename: [first_image_name]_c.webp")
    print("  • Auto-numbers if file exists (no overwrite)")
    print("  • Supports JPG, JPEG, PNG, and WEBP formats")
    print("  • No white spaces - images scaled to match")
    print("  • PNG transparency converted to white background")
    print("  • EXIF orientation auto-fixes rotated photos")
    print("  • Adjustable black border between images")
    print("\n⚠️  Close this window to exit the application.")
    print("="*60 + "\n")
    
    # Create and run GUI
    app = ImageCombinerGUI()
    app.run()

if __name__ == "__main__":
    main()

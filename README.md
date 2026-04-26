# SimpleCollage
A simple drag and drop collage maker using python. Great for creating a simple single picture to compare two existing pictures. Build with AI.

Sample output:
<img width="4202" height="2560" alt="SimpleCombine sample - Fujifilm Filter preview" src="https://github.com/user-attachments/assets/17e1ea80-eb45-46e1-984b-4e80e6284357" />


================================================================================
                            IMAGE COMBINER - README
================================================================================

A professional drag-and-drop GUI application that combines two images into a 
single, perfectly aligned image without any white spaces. The application 
intelligently scales images to match dimensions and adds an adjustable border 
between them for visual separation.

================================================================================
DESIGN SPECIFICATIONS & INTENTIONS
================================================================================

CORE REQUIREMENTS:
- Input Formats: JPG, JPEG, PNG, WEBP
- Output Format: WEBP (with normal compression, quality 85)
- Layout Logic:
  * Both portrait images → Side by side (first on LEFT, second on RIGHT)
  * Any landscape or mixed orientation → Stacked (first on TOP, second on BOTTOM)

KEY FEATURES:
1. No White Spaces - Images scaled to match exact dimensions
2. Smart Scaling - Higher resolution images scaled DOWN to match lower resolution (no upscaling = no blurring)
3. Adjustable Border - Customizable width (0-50px) and color (Black, White, Gray, Dark Gray, or Custom RGB)
4. Custom Filename Naming - Format: [PREFIX][left_image_name][SUFFIX].webp
   - Prefix field (empty by default, e.g., "Africa_")
   - Suffix field (default "_c")
   - Invalid characters automatically sanitized to underscores
   - Reset button to restore defaults
5. EXIF Orientation Handling - Auto-corrects rotated photos from cameras/phones
6. PNG Transparency - Converts transparent areas to white background
7. Auto-Numbering - Prevents overwrites by adding _1, _2, etc.
8. Drag & Drop Interface - Modern GUI with drag-and-drop zones
9. Real-time Preview - Shows output filename as you type
10. Input Validation - Real-time warnings for invalid characters

QUALITY ASSURANCE:
- No upscaling policy prevents pixelation and blurring
- Memory protection limits images to under 100 megapixels
- Aspect ratio warnings for significantly different proportions
- Comprehensive error handling with detailed messages
- Filename sanitization replaces invalid characters with underscores

================================================================================
DEPENDENCIES
================================================================================

REQUIRED PYTHON PACKAGES:
- Pillow (10.0+): Image processing, EXIF handling, format conversion
- customtkinter (5.0+): Modern GUI widgets and dark theme
- tkinterdnd2 (latest): Drag-and-drop file functionality

INSTALLATION COMMAND:
python -m pip install pillow customtkinter tkinterdnd2

SYSTEM REQUIREMENTS:
- Python: 3.10 or higher
- OS: Windows, macOS, or Linux (cross-platform)
- RAM: Minimum 512MB, 2GB+ recommended for large images
- Storage: Output folder with write permissions

================================================================================
INSTALLATION & USAGE
================================================================================

QUICK START:
1. Save the script as image_combiner.py
2. Install dependencies: python -m pip install pillow customtkinter tkinterdnd2
3. Run the application: python image_combiner.py

USAGE WORKFLOW:
1. Drag & drop first image to LEFT zone (or click to browse)
2. Drag & drop second image to RIGHT zone
3. Customize filename (optional):
   - Enter prefix (e.g., "Africa_")
   - Enter suffix (default "_c")
   - Click reset button to restore defaults
4. Adjust border settings (optional):
   - Border width: 0-50 pixels
   - Border color: Black, White, Gray, Dark Gray, or Custom RGB
5. Click "GENERATE COMBINED IMAGE"
6. Find output in the automatically created 'output' folder

EXAMPLE WORKFLOW:
- Load bird.jpg (left) + bird_color.webp (right) → Output: bird_c.webp
- Change suffix to _submission → Output preview: bird_submission.webp
- Replace left image with frog.jpg → Output: frog_submission.webp
- Type "Africa_" as prefix → Output: Africa_frog_submission.webp
- Click reset button → Output: frog_c.webp

================================================================================
TECHNICAL SPECIFICATIONS
================================================================================

RESOLUTION HANDLING:
- Target Dimension: Lower resolution image determines maximum quality
- Scaling Algorithm: Lanczos resampling (high-quality)
- Border Implementation: Background color with image positioning offsets

LAYOUT CALCULATIONS:
Side-by-Side (both portrait):
  target_height = min(img1.height, img2.height)
  output_width = (img1.width × scale1) + border + (img2.width × scale2)
  output_height = target_height

Stacked (landscape or mixed):
  target_width = min(img1.width, img2.width)
  output_width = target_width
  output_height = (img1.height × scale1) + border + (img2.height × scale2)

EXIF ORIENTATION VALUES HANDLED:
- Orientation 6 → Rotate 90° counter-clockwise (common for phone portraits)
- Orientation 8 → Rotate 90° clockwise
- Orientation 3 → Rotate 180°
- Other values for mirrored/flipped orientations

FILENAME SANITIZATION:
Invalid characters < > : " / \ | ? * are automatically replaced with underscores _

================================================================================
KNOWN LIMITATIONS
================================================================================

1. PNG Transparency - Converted to white background (not preserved)
2. Extreme Aspect Ratios - Very wide combined with very tall images may produce uneven results (warning provided)
3. Maximum Image Size - 100 megapixel limit to prevent memory issues
4. Batch Processing - One pair at a time (no batch mode)

================================================================================
TROUBLESHOOTING
================================================================================

ISSUE: "Module not found"
SOLUTION: Run python -m pip install pillow customtkinter tkinterdnd2

ISSUE: Images rotated incorrectly
SOLUTION: EXIF handling should fix automatically; ensure original files aren't manually rotated

ISSUE: Large images slow/error
SOLUTION: Reduce image size or increase MAX_IMAGE_PIXELS constant (not recommended)

ISSUE: Drag-and-drop not working
SOLUTION: Try clicking zone to browse files instead

ISSUE: White background in PNG
SOLUTION: Expected behavior (converted from transparency)

ISSUE: Invalid characters in filename
SOLUTION: They are automatically replaced with underscores; check warning messages

================================================================================
DESIGN PHILOSOPHY
================================================================================

This tool was built with the following principles:

1. Never sacrifice quality - No upscaling means no artificial blurring
2. User-friendly first - Drag-and-drop interface with visual feedback
3. Professional output - Clean, border-separated images without distracting backgrounds
4. Respects original intent - First image maintains position priority (left/top)
5. Error transparency - Clear error messages at every failure point
6. Flexible naming - Customizable prefix/suffix with sanitization

================================================================================
CREDITS
================================================================================

Built with Python 3.10.11
Last Updated: 2026

Credits:
- Pillow - Python Imaging Library
- CustomTkinter - Modern UI widgets
- TkinterDnD2 - Drag-and-drop functionality

================================================================================

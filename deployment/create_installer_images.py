"""
Create installer images for WiX MSI
Converts the icon to banner and dialog BMP images
Requires: pip install pillow
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def create_banner_image():
    """Create banner image (493x58) with logo"""
    # WiX banner size
    width, height = 493, 58
    
    # Create white background
    banner = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(banner)
    
    # Try to load and add icon
    icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
    if icon_path.exists():
        try:
            icon = Image.open(icon_path)
            # Resize icon to fit banner height with some padding
            icon_size = height - 10
            icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            # Paste icon on left side
            banner.paste(icon, (5, 5), icon if icon.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Could not load icon: {e}")
    
    # Add text
    try:
        # Try to use a nice font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text = "Chat Yapper Setup"
        # Position text to the right of icon
        draw.text((height + 10, 15), text, fill='#1e3a8a', font=font)
    except Exception as e:
        print(f"Could not add text: {e}")
    
    # Save as BMP
    output_path = Path(__file__).parent / 'banner.bmp'
    banner.save(output_path, 'BMP')
    print(f"Created banner: {output_path}")
    return output_path

def create_dialog_image():
    """Create dialog background image (493x312) with logo"""
    # WiX dialog size
    width, height = 493, 312
    
    # Create gradient background (light blue to white)
    dialog = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(dialog)
    
    # Create a subtle gradient
    for y in range(height):
        # Gradient from light blue to white
        r = int(230 + (255 - 230) * y / height)
        g = int(240 + (255 - 240) * y / height)
        b = 255
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Try to load and add icon in center
    icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
    if icon_path.exists():
        try:
            icon = Image.open(icon_path)
            # Resize icon (larger for dialog)
            icon_size = 128
            icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            # Center the icon
            x = (width - icon_size) // 2
            y = (height - icon_size) // 2 - 30
            dialog.paste(icon, (x, y), icon if icon.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Could not load icon: {e}")
    
    # Save as BMP
    output_path = Path(__file__).parent / 'dialog.bmp'
    dialog.save(output_path, 'BMP')
    print(f"Created dialog: {output_path}")
    return output_path

if __name__ == "__main__":
    print("Creating installer images...")
    
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("ERROR: Pillow not installed!")
        print("Install with: pip install pillow")
        exit(1)
    
    try:
        banner = create_banner_image()
        dialog = create_dialog_image()
        
        print("\n" + "="*60)
        print("Installer images created successfully!")
        print("="*60)
        print(f"\nBanner: {banner}")
        print(f"Dialog: {dialog}")
        print("\nThese images will be used in the MSI installer.")
    except Exception as e:
        print(f"Error creating images: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

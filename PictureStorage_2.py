#!/usr/bin/env python3
"""
File to Binary Image Converter
Converts any file to/from binary images (PNG format)
Author: Andrea Salomone
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import math
import os
import re
from pathlib import Path
from glob import glob
from collections import defaultdict


def format_size(bytes_value):
    """Format bytes into human-readable size (B, KB, MB, GB)"""
    if bytes_value < 1024:
        return f"{bytes_value} byte"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024:.2f} MB"
    else:
        return f"{bytes_value / 1024 / 1024 / 1024:.2f} GB"


def print_progress_bar(iteration, total, prefix='', length=40):
    """Print a progress bar to console"""
    if total == 0:
        return
    
    percent = (100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    print(f'\r{prefix} [{bar}] {percent:.1f}% ({iteration}/{total})', end='', flush=True)
    
    # Print newline when complete
    if iteration == total:
        print()


def encrypt_file():
    """Convert any file to binary images"""
    print("\n" + "=" * 70)
    print("FILE TO BINARY IMAGE ENCRYPTION")
    print("=" * 70)
    
    # ===== STEP 1: INPUT FILE PATH =====
    input_file_path = input("\nEnter file path: ").strip()
    
    # Verify file exists
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"File '{input_file_path}' does not exist.")
    
    # Read file in binary
    with open(input_file_path, 'rb') as f:
        file_bytes = f.read()
    
    # Extract base name, extension and directory
    file_path_obj = Path(input_file_path)
    base_name = file_path_obj.stem  # name without extension
    file_extension = file_path_obj.suffix.lstrip('.')  # extension without dot
    input_directory = file_path_obj.parent  # file directory
    
    if not file_extension:
        file_extension = "bin"
    
    print(f"\n✓ File loaded: {input_file_path}")
    print(f"  Base name: {base_name}")
    print(f"  Extension: .{file_extension}")
    print(f"  File size: {len(file_bytes)} bytes")
    print(f"  Directory: {input_directory}")
    
    # ===== STEP 2: CONVERT TO BINARY =====
    binary_string = ''.join(format(byte, '08b') for byte in file_bytes)
    binary_data = [int(bit) for bit in binary_string]
    
    n = len(binary_data)
    
    # Calculate number of images needed (max 1000x1000 = 1,000,000 pixels per image)
    max_pixels_per_image = 1000 * 1000
    num_images = math.ceil(n / max_pixels_per_image)
    
    # Format size
    size_display = format_size(len(file_bytes))
    
    print(f"\n✓ Binary data generated")
    print(f"  Total bits: {n:,}")
    print(f"  Number of images needed: {num_images}")
    
    # ===== STEP 3: CONFIRM ENCRYPTION =====
    print(f"\n{'='*70}")
    print(f"PROCEED WITH IMAGE GENERATION?")
    print(f"{'='*70}")
    print(f"  📄 File: {base_name}.{file_extension}")
    print(f"  💾 Size: {size_display}")
    print(f"  🖼️  Images to generate: {num_images}")
    print(f"  📁 Save to: {input_directory}")
    print(f"{'='*70}")
    
    proceed = input("\nProceed? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Operation cancelled.")
        return
    else:
        print("✓ Proceeding...")
    
    # ===== STEP 4: GENERATE IMAGES =====
    print(f"\n{'='*70}")
    print("GENERATING IMAGES...")
    print(f"{'='*70}\n")
    
    generated_files = []
    
    for image_num in range(num_images):
        # Calculate start and end index for this chunk
        start_idx = image_num * max_pixels_per_image
        end_idx = min(start_idx + max_pixels_per_image, n)
        
        # Extract data for this image
        chunk_data = binary_data[start_idx:end_idx]
        chunk_size = len(chunk_data)
        
        # Calculate square matrix dimensions for this chunk
        size = math.ceil(np.sqrt(chunk_size))
        
        # Create matrix
        dataMatrix = np.full((size, size), -1, dtype=int)  # fill with -1 (red padding)
        
        # Fill with data
        for idx, bit in enumerate(chunk_data):
            row = idx // size
            col = idx % size
            dataMatrix[row, col] = bit
        
        # Create RGB image
        img_array = np.zeros((size, size, 3), dtype=np.uint8)
        
        for row in range(size):
            for col in range(size):
                if dataMatrix[row, col] == 0:
                    img_array[row, col] = [255, 255, 255]  # white
                elif dataMatrix[row, col] == 1:
                    img_array[row, col] = [0, 0, 0]        # black
                else:  # -1
                    img_array[row, col] = [255, 0, 0]      # red (padding)
        
        # Save image in same directory as original file
        filename = f"{base_name}_{image_num + 1:03d}_{file_extension}.png"
        filepath = os.path.join(input_directory, filename)
        img = Image.fromarray(img_array, mode='RGB')
        img.save(filepath)
        
        generated_files.append(filename)
        
        # Print progress
        print_progress_bar(image_num + 1, num_images, prefix="  Encoding")
    
    print(f"\n{'='*70}")
    print(f"✓ COMPLETE!")
    print(f"  Images generated: {len(generated_files)}")
    print(f"\n  Files created:")
    for f in generated_files:
        print(f"    - {f}")
    print(f"  Path: {input_directory}")
    print(f"{'='*70}")


def decrypt_single_file(image_file_path, image_directory):
    """Reconstruct a single file from binary images"""
    # Extract base name and extension from image filename
    # Format: FileName_001_pdf.png
    image_filename = os.path.basename(image_file_path)
    match = re.match(r'^(.+?)_(\d{3})_([a-zA-Z0-9]+)\.png$', image_filename)
    
    if not match:
        raise ValueError(f"Invalid filename format. Expected: Name_###_extension.png")
    
    base_name = match.group(1)
    file_extension = match.group(3)
    
    # ===== STEP 2: FIND ALL FILES IN SERIES =====
    # Search for all files with same base name and extension
    pattern = os.path.join(image_directory, f"{base_name}_*_{file_extension}.png")
    matching_files = sorted(glob(pattern))
    
    if not matching_files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    
    print(f"\n  Base name: {base_name}")
    print(f"  Original file extension: .{file_extension}")
    print(f"  Series found: {len(matching_files)} image(s)")
    
    # ===== STEP 3: EXTRACT BINARY DATA FROM IMAGES =====
    binary_data_reconstructed = []
    total_images = len(matching_files)
    
    for idx, image_path in enumerate(matching_files, 1):
        # Open image
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # Convert RGB to binary values (-1, 0, 1)
        height, width = img_array.shape[:2]
        
        pixels_extracted = 0
        
        for row in range(height):
            for col in range(width):
                r, g, b = img_array[row, col, :3]
                
                # Recognize color
                if r == 255 and g == 255 and b == 255:  # white
                    binary_data_reconstructed.append(0)
                    pixels_extracted += 1
                elif r == 0 and g == 0 and b == 0:      # black
                    binary_data_reconstructed.append(1)
                    pixels_extracted += 1
                elif r == 255 and g == 0 and b == 0:    # red (padding - STOP)
                    # Reached padding, stop for this file
                    break
        
        # Print progress
        print_progress_bar(idx, total_images, prefix="  Decoding")
    
    # ===== STEP 4: CONVERT BINARY BITS TO BYTES =====
    # Ensure bits are multiple of 8
    num_complete_bytes = len(binary_data_reconstructed) // 8
    bits_to_use = num_complete_bytes * 8
    
    # Convert bits to bytes
    reconstructed_bytes = bytearray()
    for i in range(0, bits_to_use, 8):
        byte_bits = binary_data_reconstructed[i:i+8]
        byte_value = int(''.join(map(str, byte_bits)), 2)
        reconstructed_bytes.append(byte_value)
    
    # ===== STEP 5: SAVE RECONSTRUCTED FILE =====
    output_filename = f"{base_name}.{file_extension}"
    output_file_path = os.path.join(image_directory, output_filename)
    
    # Check if file already exists
    if os.path.exists(output_file_path):
        print(f"  ⚠️  File '{output_filename}' already exists, skipping...")
        return False
    else:
        with open(output_file_path, 'wb') as f:
            f.write(reconstructed_bytes)
        print(f"  ✓ {output_filename} ({format_size(len(reconstructed_bytes))})")
        return True


def decrypt_file():
    """Reconstruct original file(s) from binary images"""
    print("\n" + "=" * 70)
    print("BINARY IMAGE TO FILE DECRYPTION")
    print("=" * 70)
    
    # ===== STEP 1: INPUT IMAGE FILE PATH OR DIRECTORY =====
    input_path = input("\nEnter path of an image or directory containing images: ").strip()
    
    # Verify path exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Path '{input_path}' does not exist.")
    
    # Check if input is directory or file
    if os.path.isdir(input_path):
        # Directory mode: find all encrypted file series
        directory = input_path
        
        # Find all PNG files in directory
        png_files = glob(os.path.join(directory, "*.png"))
        
        if not png_files:
            raise FileNotFoundError(f"No PNG files found in '{directory}'")
        
        print(f"\n✓ Directory loaded: {directory}")
        print(f"  PNG files found: {len(png_files)}")
        
        # Group files by base name (identify unique encrypted files)
        file_groups = defaultdict(list)
        
        for png_file in png_files:
            filename = os.path.basename(png_file)
            match = re.match(r'^(.+?)_(\d{3})_([a-zA-Z0-9]+)\.png$', filename)
            
            if match:
                base_name = match.group(1)
                file_groups[base_name].append(png_file)
        
        if not file_groups:
            raise ValueError("No valid encrypted file series found in directory")
        
        print(f"\n✓ Encrypted file series detected: {len(file_groups)}")
        for base_name, files in file_groups.items():
            print(f"  - {base_name} ({len(files)} image(s))")
        
        # ===== DECRYPT ALL FILES =====
        print(f"\n{'='*70}")
        print("RECONSTRUCTING ALL FILES...")
        print(f"{'='*70}\n")
        
        successful = 0
        
        for base_name, files in sorted(file_groups.items()):
            try:
                # Use first file from series to start decryption
                result = decrypt_single_file(files[0], directory)
                if result:
                    successful += 1
            except Exception as e:
                print(f"  ❌ Error decrypting {base_name}: {e}")
        
        print(f"\n{'='*70}")
        print(f"✓ COMPLETE!")
        print(f"  Files reconstructed: {successful}/{len(file_groups)}")
        print(f"  Location: {directory}")
        print(f"{'='*70}")
    
    else:
        # Single file mode
        image_file_path = input_path
        image_filename = os.path.basename(image_file_path)
        directory = os.path.dirname(image_file_path) or '.'
        
        print(f"\n✓ Image loaded: {image_filename}")
        
        # ===== DECRYPT SINGLE FILE =====
        print(f"\n{'='*70}")
        print("RECONSTRUCTING FILE...")
        print(f"{'='*70}\n")
        
        try:
            result = decrypt_single_file(image_file_path, directory)
            
            if result:
                print(f"\n{'='*70}")
                print(f"✓ FILE SUCCESSFULLY RECONSTRUCTED!")
                print(f"{'='*70}")
                print(f"  Location: {directory}")
                print(f"{'='*70}")
            else:
                print(f"\n{'='*70}")
                print(f"⚠️  File already exists")
                print(f"{'='*70}")
        except Exception as e:
            raise e


def main():
    """Main program"""
    print("\n" + "=" * 70)
    print("FILE ↔ BINARY IMAGE CONVERTER")
    print("=" * 70)
    print("\nWhat would you like to do?")
    print("  1. Encrypt (convert file to images)")
    print("  2. Decrypt (convert images back to file)")
    print("=" * 70)
    
    choice = input("\nChoose (1 or 2): ").strip()
    
    if choice == '1':
        encrypt_file()
    elif choice == '2':
        decrypt_file()
    else:
        print("Invalid choice. Please enter 1 or 2.")
        main()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)

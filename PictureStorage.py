#!/usr/bin/env python3
"""
File to Binary Image Converter (RGB 24-bit Streaming version)
Converts any file to/from binary images using full RGB color space
- Streaming: processes file in chunks (low memory usage)
- Large images: 10000×10000 pixels (~286 MB per image)
- Real-time progress: shows bytes processed immediately
- Maximum file size: 237 Yottabytes (2^96 pixels × 3 bytes)
Author: Andrea Salomone
"""

import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb check
import math
import os
import re
import time
from pathlib import Path
from glob import glob
from collections import defaultdict


def format_size(bytes_value):
    """Format bytes into human-readable size (B, KB, MB, GB, TB, PB, EB, ZB, YB)"""
    if bytes_value < 1024:
        return f"{bytes_value} byte"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024:.2f} MB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024 / 1024:.2f} GB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024 / 1024 / 1024:.2f} TB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024 / 1024 / 1024 / 1024:.2f} PB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024 / 1024 / 1024 / 1024 / 1024:.2f} EB"
    elif bytes_value < 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024:
        return f"{bytes_value / 1024 / 1024 / 1024 / 1024 / 1024 / 1024 / 1024:.2f} ZB"
    else:
        return f"{bytes_value / 1024 / 1024 / 1024 / 1024 / 1024 / 1024 / 1024 / 1024:.2f} YB"


def print_progress_bar(iteration, total, prefix='', length=40):
    """Print a progress bar to console"""
    if total == 0:
        return
    
    percent = (100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    print(f'\r{prefix} [{bar}] {percent:.1f}% ({iteration}/{total})', end='', flush=True)
    
    if iteration == total:
        print()


def print_bytes_progress(bytes_processed, total_bytes, prefix='', length=40, start_time=None):
    """Print progress bar based on bytes processed with speed indicator"""
    if total_bytes == 0:
        return
    
    percent = (100 * (bytes_processed / float(total_bytes)))
    filled_length = int(length * bytes_processed // total_bytes)
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    # Format bytes
    processed_str = format_size(bytes_processed)
    total_str = format_size(total_bytes)
    
    # Calculate speed if start_time provided
    speed_info = ""
    if start_time and bytes_processed > 0:
        elapsed = time.time() - start_time
        if elapsed > 0:
            bytes_per_sec = bytes_processed / elapsed
            speed_info = f" | {format_size(bytes_per_sec)}/s"
            
            # Estimate time remaining
            if bytes_processed < total_bytes:
                bytes_remaining = total_bytes - bytes_processed
                eta_seconds = bytes_remaining / bytes_per_sec
                if eta_seconds < 60:
                    speed_info += f" | ETA: {eta_seconds:.0f}s"
                elif eta_seconds < 3600:
                    speed_info += f" | ETA: {eta_seconds/60:.1f}m"
                else:
                    speed_info += f" | ETA: {eta_seconds/3600:.1f}h"
    
    print(f'\r{prefix} [{bar}] {percent:.1f}% ({processed_str}/{total_str}){speed_info}', end='', flush=True)
    
    if bytes_processed >= total_bytes:
        print()


def create_header_pixels(complete_pixels, extra_bits):
    """Create 5 header pixels with metadata"""
    header_pixels = []
    
    # Encode complete_pixels into 96 bits (12 bytes) for pixels 0-3
    length_bytes = []
    temp = complete_pixels
    for _ in range(12):
        length_bytes.append(temp & 0xFF)
        temp >>= 8
    length_bytes.reverse()  # Big-endian
    
    # Create header pixels 0-3 (length metadata)
    for i in range(4):
        r = length_bytes[i * 3]
        g = length_bytes[i * 3 + 1]
        b = length_bytes[i * 3 + 2]
        header_pixels.append([r, g, b])
    
    # Create header pixel 4 (extra bits)
    header_pixels.append([0, 0, extra_bits])
    
    return header_pixels


def encrypt_file():
    """Convert any file to RGB binary images (24 bits per pixel) using streaming"""
    print("\n" + "=" * 70)
    print("FILE TO BINARY IMAGE ENCRYPTION (RGB 24-bit STREAMING)")
    print("=" * 70)
    
    # ===== STEP 1: INPUT FILE PATH =====
    input_file_path = input("\nEnter file path: ").strip()
    
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"File '{input_file_path}' does not exist.")
    
    # Get file size without loading entire file
    file_size = os.path.getsize(input_file_path)
    
    file_path_obj = Path(input_file_path)
    base_name = file_path_obj.stem
    file_extension = file_path_obj.suffix.lstrip('.')
    input_directory = file_path_obj.parent
    
    if not file_extension:
        file_extension = "bin"
    
    print(f"\n✓ File info:")
    print(f"  Path: {input_file_path}")
    print(f"  Base name: {base_name}")
    print(f"  Extension: .{file_extension}")
    print(f"  File size: {file_size} bytes ({format_size(file_size)})")
    print(f"  Directory: {input_directory}")
    
    # ===== STEP 2: CALCULATE METADATA (without loading file) =====
    total_bits = file_size * 8
    complete_pixels = total_bits // 24
    extra_bits = total_bits % 24
    
    # Header: 5 pixels (4 for length + 1 for extra bits)
    header_pixels = 5
    data_pixels = complete_pixels + (1 if extra_bits > 0 else 0)
    total_pixels_needed = header_pixels + data_pixels
    
    # Calculate images needed (max 10000x10000 pixels per image)
    max_pixels_per_image = 10000 * 10000  # 100 million pixels = ~286 MB
    num_images = math.ceil(total_pixels_needed / max_pixels_per_image)
    
    print(f"\n✓ Encoding metadata calculated:")
    print(f"  Total bits: {total_bits:,}")
    print(f"  Complete pixels (24-bit): {complete_pixels:,}")
    print(f"  Extra bits: {extra_bits}")
    print(f"  Total pixels needed: {total_pixels_needed:,} (header: 5 + data: {data_pixels:,})")
    print(f"  Images needed: {num_images}")
    print(f"  Image size: 10000×10000 (~286 MB per image)")
    
    # ===== STEP 3: CONFIRM ENCRYPTION =====
    print(f"\n{'='*70}")
    print(f"PROCEED WITH IMAGE GENERATION?")
    print(f"{'='*70}")
    print(f"  📄 File: {base_name}.{file_extension}")
    print(f"  💾 Size: {format_size(file_size)}")
    print(f"  🖼️  Images to generate: {num_images}")
    print(f"  📁 Save to: {input_directory}")
    print(f"  🎨 Encoding: RGB 24-bit streaming (3 bytes per pixel)")
    print(f"  ⚡ Memory efficient: processes in chunks")
    print(f"{'='*70}")
    
    proceed = input("\nProceed? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Operation cancelled.")
        return
    
    print("✓ Proceeding with streaming encoding...")
    
    # ===== STEP 4: STREAMING ENCRYPTION =====
    print(f"\n{'='*70}")
    print("ENCODING FILE...")
    print(f"{'='*70}\n")
    
    generated_files = []
    bytes_processed = 0
    start_time = time.time()
    
    # Update interval for progress (every 1 MB or every chunk, whichever is smaller)
    update_interval = min(1024 * 1024, file_size // 100 if file_size > 0 else 1024 * 1024)
    last_update_bytes = 0
    
    with open(input_file_path, 'rb') as f:
        for image_num in range(num_images):
            # Calculate how many pixels this image should contain
            if image_num == 0:
                # First image: header + data
                pixels_in_image = min(max_pixels_per_image, total_pixels_needed)
                data_pixels_in_image = pixels_in_image - header_pixels
            else:
                # Subsequent images: only data
                pixels_already_written = header_pixels + (image_num - 1) * max_pixels_per_image + (min(max_pixels_per_image, total_pixels_needed) - header_pixels)
                pixels_remaining = total_pixels_needed - pixels_already_written
                pixels_in_image = min(max_pixels_per_image, pixels_remaining)
                data_pixels_in_image = pixels_in_image
            
            # Create pixel list for this image
            image_pixels = []
            
            # Add header pixels if first image
            if image_num == 0:
                image_pixels.extend(create_header_pixels(complete_pixels, extra_bits))
            
            # Read data bytes for this image (3 bytes per pixel)
            bytes_to_read = data_pixels_in_image * 3
            
            # Handle last pixel with extra bits
            if image_num == num_images - 1 and extra_bits > 0:
                # Last image may have extra bits pixel
                bytes_to_read = (data_pixels_in_image - 1) * 3 + math.ceil(extra_bits / 8)
            
            # Read in smaller chunks to update progress more frequently
            chunk_size = min(bytes_to_read, 10 * 1024 * 1024)  # 10 MB chunks
            chunk_bytes = bytearray()
            
            while len(chunk_bytes) < bytes_to_read:
                remaining = bytes_to_read - len(chunk_bytes)
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                chunk_bytes.extend(data)
                bytes_processed += len(data)
                
                # Update progress bar
                if bytes_processed - last_update_bytes >= update_interval or bytes_processed == file_size:
                    print_bytes_progress(bytes_processed, file_size, prefix="  Reading", start_time=start_time)
                    last_update_bytes = bytes_processed
            
            # Convert bytes directly to RGB pixels (no bit expansion!)
            for i in range(0, len(chunk_bytes), 3):
                if i + 2 < len(chunk_bytes):
                    # Complete pixel
                    r, g, b = chunk_bytes[i], chunk_bytes[i+1], chunk_bytes[i+2]
                    image_pixels.append([r, g, b])
                elif i + 1 < len(chunk_bytes):
                    # Partial pixel (2 bytes + padding)
                    r, g = chunk_bytes[i], chunk_bytes[i+1]
                    image_pixels.append([r, g, 0])
                else:
                    # Partial pixel (1 byte + padding)
                    r = chunk_bytes[i]
                    image_pixels.append([r, 0, 0])
            
            # Calculate square dimensions
            size = math.ceil(np.sqrt(len(image_pixels)))
            
            # Create image array
            img_array = np.full((size, size, 3), 255, dtype=np.uint8)  # White padding
            
            # Fill with pixel data
            for idx, pixel in enumerate(image_pixels):
                row = idx // size
                col = idx % size
                img_array[row, col] = pixel
            
            # Save image
            filename = f"{base_name}_{image_num + 1:03d}_{file_extension}.png"
            filepath = os.path.join(input_directory, filename)
            
            print(f"\r  Saving image {image_num + 1}/{num_images}: {filename}...", end='', flush=True)
            img = Image.fromarray(img_array, mode='RGB')
            img.save(filepath)
            print(f"\r  ✓ Saved image {image_num + 1}/{num_images}: {filename}    ")
            
            generated_files.append(filename)
            
            # Clear memory
            del chunk_bytes
            del image_pixels
            del img_array
            del img
    
    # Final progress update
    if bytes_processed < file_size:
        print_bytes_progress(file_size, file_size, prefix="  Reading", start_time=start_time)
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"✓ COMPLETE!")
    print(f"  Images generated: {len(generated_files)}")
    print(f"  Total time: {elapsed_time:.2f}s")
    print(f"  Average speed: {format_size(file_size / elapsed_time)}/s")
    print(f"\n  Files created:")
    for f in generated_files:
        print(f"    - {f}")
    print(f"  Path: {input_directory}")
    print(f"  Data efficiency: {file_size / (total_pixels_needed * 3) * 100:.2f}%")
    print(f"{'='*70}")


def decrypt_single_file(image_file_path, image_directory):
    """Reconstruct a single file from RGB binary images (streaming)"""
    image_filename = os.path.basename(image_file_path)
    match = re.match(r'^(.+?)_(\d{3})_([a-zA-Z0-9]+)\.png$', image_filename)
    
    if not match:
        raise ValueError(f"Invalid filename format. Expected: Name_###_extension.png")
    
    base_name = match.group(1)
    file_extension = match.group(3)
    
    # Find all files in series
    pattern = os.path.join(image_directory, f"{base_name}_*_{file_extension}.png")
    matching_files = sorted(glob(pattern))
    
    if not matching_files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    
    print(f"\n  Base name: {base_name}")
    print(f"  Original file extension: .{file_extension}")
    print(f"  Series found: {len(matching_files)} image(s)")
    
    # Open first image to read header
    print(f"  Reading metadata from first image...")
    first_img = Image.open(matching_files[0])
    first_array = np.array(first_img)
    
    # Extract header pixels (first 5 pixels)
    header_pixels = []
    for i in range(5):
        row = i // first_array.shape[1]
        col = i % first_array.shape[1]
        r, g, b = first_array[row, col, :3]
        header_pixels.append([r, g, b])
    
    # Decode complete_pixels from header pixels 0-3
    length_bytes = []
    for i in range(4):
        length_bytes.extend(header_pixels[i])
    
    complete_pixels = 0
    for byte_val in length_bytes:
        complete_pixels = (complete_pixels << 8) | byte_val
    
    # Decode extra_bits from header pixel 4
    extra_bits = header_pixels[4][2]
    
    print(f"  Complete pixels to read: {complete_pixels:,}")
    print(f"  Extra bits to read: {extra_bits}")
    
    # Calculate total bytes to extract
    total_bytes = complete_pixels * 3
    if extra_bits > 0:
        total_bytes += math.ceil(extra_bits / 8)
    
    print(f"  Total bytes to reconstruct: {total_bytes:,} ({format_size(total_bytes)})")
    
    # Create output file
    output_filename = f"{base_name}.{file_extension}"
    output_file_path = os.path.join(image_directory, output_filename)
    
    if os.path.exists(output_file_path):
        print(f"  ⚠️  File '{output_filename}' already exists, skipping...")
        return False
    
    # Stream decode: process images one by one
    bytes_written = 0
    bytes_target = complete_pixels * 3
    start_time = time.time()
    
    # Update interval
    update_interval = min(1024 * 1024, total_bytes // 100 if total_bytes > 0 else 1024 * 1024)
    last_update_bytes = 0
    
    with open(output_file_path, 'wb') as out_file:
        for idx, image_path in enumerate(matching_files, 1):
            print(f"\r  Processing image {idx}/{len(matching_files)}...", end='', flush=True)
            
            img = Image.open(image_path)
            img_array = np.array(img)
            
            height, width = img_array.shape[:2]
            
            # Start from pixel 5 for first image (skip header)
            start_pixel = 5 if idx == 1 else 0
            
            for row in range(height):
                for col in range(width):
                    pixel_idx = row * width + col
                    
                    if pixel_idx < start_pixel:
                        continue
                    
                    if bytes_written >= bytes_target:
                        # Handle extra bits if any
                        if extra_bits > 0 and bytes_written < total_bytes:
                            r, g, b = img_array[row, col, :3]
                            extra_bytes_needed = math.ceil(extra_bits / 8)
                            
                            if bytes_written < total_bytes:
                                out_file.write(bytes([r]))
                                bytes_written += 1
                            if bytes_written < total_bytes and extra_bytes_needed > 1:
                                out_file.write(bytes([g]))
                                bytes_written += 1
                            if bytes_written < total_bytes and extra_bytes_needed > 2:
                                out_file.write(bytes([b]))
                                bytes_written += 1
                        break
                    
                    r, g, b = img_array[row, col, :3]
                    
                    # Write RGB as 3 bytes
                    if bytes_written < bytes_target:
                        out_file.write(bytes([r]))
                        bytes_written += 1
                    if bytes_written < bytes_target:
                        out_file.write(bytes([g]))
                        bytes_written += 1
                    if bytes_written < bytes_target:
                        out_file.write(bytes([b]))
                        bytes_written += 1
                    
                    # Update progress
                    if bytes_written - last_update_bytes >= update_interval or bytes_written == total_bytes:
                        print_bytes_progress(bytes_written, total_bytes, prefix="  Writing", start_time=start_time)
                        last_update_bytes = bytes_written
                
                if bytes_written >= total_bytes:
                    break
            
            # Clear memory
            del img
            del img_array
            
            if bytes_written >= total_bytes:
                break
    
    # Final progress update
    if bytes_written < total_bytes:
        print_bytes_progress(total_bytes, total_bytes, prefix="  Writing", start_time=start_time)
    
    elapsed_time = time.time() - start_time
    print(f"\n  ✓ {output_filename} ({format_size(bytes_written)}) - {elapsed_time:.2f}s")
    return True


def decrypt_file():
    """Reconstruct original file(s) from RGB binary images"""
    print("\n" + "=" * 70)
    print("BINARY IMAGE TO FILE DECRYPTION (RGB 24-bit STREAMING)")
    print("=" * 70)
    
    input_path = input("\nEnter path of an image or directory containing images: ").strip()
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Path '{input_path}' does not exist.")
    
    if os.path.isdir(input_path):
        directory = input_path
        png_files = glob(os.path.join(directory, "*.png"))
        
        if not png_files:
            raise FileNotFoundError(f"No PNG files found in '{directory}'")
        
        print(f"\n✓ Directory loaded: {directory}")
        print(f"  PNG files found: {len(png_files)}")
        
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
        
        print(f"\n{'='*70}")
        print("RECONSTRUCTING ALL FILES...")
        print(f"{'='*70}\n")
        
        successful = 0
        
        for base_name, files in sorted(file_groups.items()):
            try:
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
        image_file_path = input_path
        image_filename = os.path.basename(image_file_path)
        directory = os.path.dirname(image_file_path) or '.'
        
        print(f"\n✓ Image loaded: {image_filename}")
        
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
    print("FILE ↔ BINARY IMAGE CONVERTER (RGB 24-bit STREAMING)")
    print("Large images: 10000×10000 pixels (~286 MB per image)")
    print("Maximum file size: 237 Yottabytes")
    print("Memory efficient: streams data in chunks")
    print("Real-time progress tracking with speed & ETA")
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

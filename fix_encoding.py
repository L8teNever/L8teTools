import os

def clean_app_py():
    with open('app.py', 'rb') as f:
        content = f.read()

    # Find the start of the UTF-16 mess.
    # We look for the sequence that likely started the mess. 
    # Or simpler: find the first null byte. 
    # Valid UTF-8 source code shouldn't have null bytes.
    
    first_null = content.find(b'\x00')
    if first_null != -1:
        print(f"Found null byte at index {first_null}. Truncating...")
        # Backtrack to the last newline before this to be safe?
        # Or just cut there. The null byte is likely start of the appended UTF-16 string.
        # But we might have appended UTF-16 right after a valid character.
        # Let's clean up: take content up to first_null.
        clean_content = content[:first_null]
        
        # We also need to remove the text I supposedly wrote successfuly before the utf-16 mess? 
        # Step 171 created temp_routes.py and appended it.
        # If Step 171 wrote UTF-8 to temp_routes.py, but `type >>` converted it?
        # PowerShell `type` (Get-Content) might have auto-converted to UTF-16 when piping to `>>`.
        
        # So we probably effectively damaged the file from the moment we used `>>`.
        # The content before the append should be fine.
        
        with open('app.py', 'wb') as f:
            f.write(clean_content)
        print("Cleaned app.py")
    else:
        print("No null bytes found. File might be UTF-8 but maybe still corrupt logic?")

if __name__ == "__main__":
    clean_app_py()

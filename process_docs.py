import os
import re
from bs4 import BeautifulSoup

class PineScriptDocsProcessor:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = os.path.join(input_dir, "processed")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def clean_navigation(self, text):
        """Remove navigation elements and links"""
        # Remove navigation sections
        text = re.sub(r'Version Version.*?Auto', '', text, flags=re.DOTALL)
        text = re.sub(r'\* \[.*?\n', '', text)
        text = re.sub(r'Copyright © .*?TradingView.*?\n', '', text)
        text = re.sub(r'On this page.*?\n', '', text)
        return text
        
    def extract_code_blocks(self, text):
        """Preserve and clean code blocks"""
        # Find Pine Script code blocks
        code_blocks = re.findall(r'```(?:pine)?(.*?)```', text, re.DOTALL)
        clean_blocks = []
        for block in code_blocks:
            # Clean the code block
            clean_block = block.strip()
            if clean_block:
                clean_blocks.append(f"```pine\n{clean_block}\n```")
        return clean_blocks
        
    def extract_function_docs(self, text):
        """Extract function documentation"""
        # Find function descriptions
        functions = re.findall(r'@function.*?@returns.*?\n', text, re.DOTALL)
        return functions
        
    def process_file(self, filename):
        """Process a single documentation file"""
        with open(os.path.join(self.input_dir, filename), 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip if no real content
        if len(content) < 100 or 'User Manual' not in content:
            return None
            
        # Clean navigation and basic structure
        content = self.clean_navigation(content)
        
        # Extract valuable parts
        code_blocks = self.extract_code_blocks(content)
        function_docs = self.extract_function_docs(content)
        
        # Extract main content sections (Q&A format in FAQ)
        sections = re.findall(r'##\s+\[(.*?)\].*?\n(.*?)(?=##|\Z)', content, re.DOTALL)
        
        # Build processed content
        processed = []
        
        if sections:
            for title, section in sections:
                if any(keyword in section.lower() for keyword in ['pine', 'script', 'function', 'indicator', 'value', 'parameter']):
                    clean_section = re.sub(r'\[\^.*?\]', '', section)  # Remove footnotes
                    clean_section = re.sub(r'\(https://.*?\)', '', clean_section)  # Remove links
                    processed.append(f"## {title}\n{clean_section.strip()}")
        
        if code_blocks:
            processed.append("\n## Code Examples\n")
            processed.extend(code_blocks)
            
        if function_docs:
            processed.append("\n## Function Documentation\n")
            processed.extend(function_docs)
            
        if not processed:
            return None
            
        # Save processed content
        output_filename = f"processed_{filename}"
        with open(os.path.join(self.output_dir, output_filename), 'w', encoding='utf-8') as f:
            f.write("\n\n".join(processed))
            
        return output_filename
        
    def process_all(self):
        """Process all markdown files in the input directory"""
        processed_files = []
        print(f"Looking for files in: {self.input_dir}")
        
        # Print all files found
        all_files = os.listdir(self.input_dir)
        print(f"Found files: {all_files}")
        
        for filename in all_files:
            if filename.endswith('.md') and filename != 'all_docs.md':
                print(f"Processing file: {filename}")
                output_file = self.process_file(filename)
                if output_file:
                    processed_files.append(output_file)
                    print(f"Successfully processed: {output_file}")
                else:
                    print(f"Skipped file: {filename} (no valid content found)")
        
        # Create a combined processed file
        with open(os.path.join(self.output_dir, 'processed_all_docs.md'), 'w', encoding='utf-8') as combined:
            for filename in processed_files:
                with open(os.path.join(self.output_dir, filename), 'r', encoding='utf-8') as f:
                    combined.write(f"\n\n# {filename[:-3]}\n\n")
                    combined.write(f.read())
                    combined.write("\n\n---\n\n")

if __name__ == "__main__":
    # Get the script's directory and set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "pinescript_docs")
    
    processor = PineScriptDocsProcessor(input_dir, "processed")
    processor.process_all()
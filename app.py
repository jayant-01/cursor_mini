import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import zipfile
import io

# Load environment variables
load_dotenv()

# Configure API key

# Load from Streamlit secrets if available, otherwise .env
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("No API key found. Please set GOOGLE_API_KEY in Streamlit Secrets or .env file.")
else:
    genai.configure(api_key=api_key)


# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

def generate_project_structure(prompt):
    system_prompt = f"""You are an expert software architect and developer. Your task is to generate a project structure as a JSON object.

    Requirements: {prompt}

    Rules:
    1. Response MUST be ONLY a valid JSON object
    2. Do not include any text outside the JSON
    3. Use proper JSON formatting with double quotes for strings
    4. Escape special characters properly

    JSON Structure:
    {{
        "files": [
            {{
                "path": "path/to/file",
                "content": "file content",
                "type": "file"  // or "directory"
            }}
        ],
        "setup": [
            "step 1",
            "step 2"
        ]
    }}
    """
    
    try:
        response = model.generate_content(system_prompt, generation_config={
            'temperature': 0.2,  # Lower temperature for more structured output
            'top_p': 0.8,
            'top_k': 40
        })
        
        # Clean the response text
        text = response.text.strip()
        
        # Remove any potential markdown code block markers
        text = text.replace('```json', '').replace('```', '')
        
        # Ensure it's a valid JSON string
        if not text.startswith('{'):
            text = text[text.find('{'):]
        if not text.endswith('}'):
            text = text[:text.rfind('}')+1]
            
        # Parse the JSON
        project_data = json.loads(text)
        
        # Validate the required keys
        if 'files' not in project_data or 'setup' not in project_data:
            raise ValueError("Missing required keys in JSON response")
            
        return project_data
        
    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error: {str(e)}")
        st.code(text, language='json')
        raise ValueError(f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error generating project structure: {str(e)}")

def create_zip_file(project_structure):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in project_structure['files']:
            if file['type'] == 'file':
                zip_file.writestr(file['path'], file['content'])
    return zip_buffer

# Set page config
st.set_page_config(page_title="Mini Cursor - Project Generator", layout="wide")

# Title and description
st.title("Mini Cursor - Project Generator")
st.markdown("Generate complete project structures using AI")

# Sidebar for API key configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Project Requirements")
    prompt = st.text_area(
        "Describe your project requirements",
        height=200,
        placeholder="Example: Create a React todo app with TypeScript and Tailwind CSS"
    )
    
    if st.button("Generate Project", type="primary"):
        if not api_key:
            st.error("Please enter your Google API Key in the sidebar")
        elif not prompt:
            st.error("Please enter project requirements")
        else:
            with st.spinner("Generating project structure..."):
                try:
                    project_structure = generate_project_structure(prompt)
                    st.session_state.project_structure = project_structure
                    st.success("Project structure generated successfully!")
                except Exception as e:
                    st.error(f"Error generating project: {str(e)}")

with col2:
    if 'project_structure' in st.session_state:
        st.subheader("Generated Project Structure")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Files", "Setup Instructions", "Architecture"])
        
        with tab1:
            for file in st.session_state.project_structure['files']:
                with st.expander(f"{file['path']} - {file.get('description', '')}"):
                    if file['type'] == 'file':
                        st.code(file['content'], line_numbers=True)
                    else:
                        st.info("Directory")
        
        with tab2:
            for step in st.session_state.project_structure['setup']:
                title = step['step'] if isinstance(step, dict) else str(step)
                with st.expander(title):
                    if isinstance(step, dict) and step.get('command'):
                        st.code(step['command'])
                    if isinstance(step, dict) and 'details' in step:
                        st.write(step['details'])
        
        with tab3:
            arch = st.session_state.project_structure.get('architecture', {})
            if isinstance(arch, dict):
                st.markdown("### Project Architecture")
                st.write(arch.get('description', 'No description available.'))
                
                st.markdown("### Main Components")
                for component in arch.get('components', []):
                    st.markdown(f"- {component}")
                    
                st.markdown("### Dependencies")
                for dep in arch.get('dependencies', []):
                    st.markdown(f"- {dep}")
                    
                st.markdown("### Development Tools")
                for tool in arch.get('development_tools', []):
                    st.markdown(f"- {tool}")
            else:
                st.error("Architecture data is not in the expected format.")
                st.write(arch)

        
        # Download button
        zip_buffer = create_zip_file(st.session_state.project_structure)
        st.download_button(
            label="Download Project as ZIP",
            data=zip_buffer.getvalue(),
            file_name="generated_project.zip",
            mime="application/zip"
        )
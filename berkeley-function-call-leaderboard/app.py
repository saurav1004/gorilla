import streamlit as st
import json
import os
import glob

# --- Configuration ---
st.set_page_config(layout="wide", page_title="BFCL Generation Viewer")

# --- Helper Functions (No Caching for Freshness) ---

def get_model_names(base_dir):
    """Scans the score directory for available models."""
    score_path = os.path.join(base_dir, "score")
    if not os.path.exists(score_path):
        return []
    # Only list directories
    models = [d for d in os.listdir(score_path) if os.path.isdir(os.path.join(score_path, d))]
    return sorted(models)

def get_score_files(base_dir, model_name):
    """Finds all score.json files for a given model."""
    model_score_path = os.path.join(base_dir, "score", model_name)
    # Recursively find score files
    files = glob.glob(os.path.join(model_score_path, "**", "*_score.json"), recursive=True)
    
    file_options = {}
    for f in files:
        filename = os.path.basename(f)
        category = filename.replace("BFCL_v4_", "").replace("_score.json", "")
        
        # Determine group based on folder path or filename
        is_live = "live" in filename or "live" in f.split(os.sep)
        group = "Live" if is_live else "Non-Live"
        
        display_name = f"[{group}] {category}"
        file_options[display_name] = f
        
    return file_options

def load_data(file_path):
    """Loads the score file line-by-line. ALWAYS Fresh from disk."""
    data = []
    stats = {}
    
    if not os.path.exists(file_path):
        return None, None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if not lines:
            return {}, []

        # 1. Try to parse the first line as Summary Stats
        # BFCL score files typically have {"accuracy":...} on line 1
        try:
            first_obj = json.loads(lines[0])
            if "accuracy" in first_obj or "correct_count" in first_obj:
                stats = first_obj
                start_index = 1 # Skip first line for data
            else:
                # If first line looks like a data entry (has 'id'), treat it as data
                stats = {}
                start_index = 0
        except:
            stats = {}
            start_index = 0

        # 2. Parse the rest as Data Entries
        for line in lines[start_index:]:
            line = line.strip()
            if not line: continue
            try:
                data.append(json.loads(line))
            except:
                continue
                
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None, None
        
    return stats, data

# --- Sidebar Controls ---

st.sidebar.title("🦍 BFCL Viewer")

# 1. Base Directory
default_path = os.path.abspath(".")
if "berkeley-function-call-leaderboard" not in default_path:
    if os.path.exists("gorilla/berkeley-function-call-leaderboard"):
        default_path = "gorilla/berkeley-function-call-leaderboard"

base_dir = st.sidebar.text_input("BFCL Root Directory", value=default_path)

# 2. Model Selection
models = get_model_names(base_dir)
if not models:
    st.sidebar.error(f"No 'score' folder found in {base_dir}")
    st.stop()

selected_model = st.sidebar.selectbox("Select Model", models)

# 3. Category Selection
file_options = get_score_files(base_dir, selected_model)
if not file_options:
    st.sidebar.warning("No score files found for this model.")
    st.stop()

sorted_keys = sorted(file_options.keys())
selected_category_name = st.sidebar.selectbox("Select Test Category", sorted_keys)
selected_file_path = file_options[selected_category_name]

# 4. Filters
st.sidebar.markdown("---")
filter_status = st.sidebar.radio("Filter Results", ["All", "Valid (Correct)", "Invalid (Incorrect)"])

# Add a manual refresh button just in case
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# --- Main Content ---

stats, data = load_data(selected_file_path)

if data is None:
    st.error(f"Could not read file: `{selected_file_path}`")
    st.stop()

if not data:
    st.warning(f"File is empty: `{selected_file_path}`")
    st.stop()

# Header Statistics
st.title(f"📊 {selected_category_name}")
st.caption(f"Path: `{selected_file_path}`")

if stats:
    cols = st.columns(4)
    cols[0].metric("Accuracy", f"{stats.get('accuracy', 0):.2%}")
    cols[1].metric("Correct", stats.get('correct_count', 0))
    cols[2].metric("Total", stats.get('total_count', 0))
    if stats.get('total_count', 0) > 0:
        incorrect = stats.get('total_count') - stats.get('correct_count', 0)
        cols[3].metric("Incorrect", incorrect)

st.markdown("---")

# --- Filtering ---
filtered_data = []
for item in data:
    # Default to False if key missing
    is_valid = item.get("valid", False)
    
    if filter_status == "Valid (Correct)" and not is_valid:
        continue
    if filter_status == "Invalid (Incorrect)" and is_valid:
        continue
    filtered_data.append(item)

# Debug message if filter returns nothing
if not filtered_data:
    st.info(f"Loaded {len(data)} items, but 0 matched filter '{filter_status}'.")
    st.stop()

# --- Pagination ---
items_per_page = 10
total_items = len(filtered_data)
total_pages = max(1, (total_items - 1) // items_per_page + 1)

st.sidebar.markdown("---")
st.sidebar.write(f"**Pagination** ({total_items} items)")
current_page = st.sidebar.number_input("Page", min_value=1, max_value=total_pages, value=1)

start_idx = (current_page - 1) * items_per_page
end_idx = min(start_idx + items_per_page, total_items)
paginated_data = filtered_data[start_idx:end_idx]

st.write(f"Showing items **{start_idx + 1} - {end_idx}** of **{total_items}**")

# --- Render Items ---

for entry in paginated_data:
    # 1. ID & Status
    test_id = entry.get("id", "Unknown ID")
    is_valid = entry.get("valid", False)
    status_icon = "✅" if is_valid else "❌"
    
    # 2. Extract Data Fields
    prompt_data = entry.get("prompt", {})
    
    # 2a. Prompt Questions (Handle list vs list-of-lists)
    questions = prompt_data.get("question", [])
    if questions and isinstance(questions[0], list):
        questions = questions[0]
    
    # 2b. Available Tools
    tools = prompt_data.get("function", [])
    
    # 2c. Results
    model_raw = entry.get("model_result_raw", "No raw output found")
    model_decoded = entry.get("model_result_decoded", "No decoded output")
    ground_truth = entry.get("possible_answer", "No ground truth found")
    error_msg = entry.get("error", None)

    with st.container():
        st.markdown(f"### {status_icon} ID: `{test_id}`")
        
        # Layout: Left (Inputs), Right (Outputs)
        col_left, col_right = st.columns([1, 1])
        
        # --- LEFT: Context ---
        with col_left:
            st.subheader("1. Input Prompt")
            if not questions:
                st.text("No question data found.")
            for q in questions:
                # Handle simple dict or object
                if isinstance(q, dict):
                    role = q.get('role', 'unknown').capitalize()
                    content = q.get('content', '')
                    if role.lower() == 'user':
                        st.info(f"**{role}:** {content}")
                    else:
                        st.text(f"{role}: {content}")
                else:
                    st.text(str(q))
            
            st.subheader("2. Available Tools")
            if tools:
                with st.expander(f"Show {len(tools)} Tool Definitions"):
                    st.json(tools)
            else:
                st.warning("No tools found in prompt data.")

        # --- RIGHT: Execution ---
        with col_right:
            st.subheader("3. Model Generation")
            st.caption("Raw Output")
            st.code(model_raw, language="json")
            
            # Optional: Show Decoded if needed
            # st.caption("Decoded")
            # st.json(model_decoded)

            st.subheader("4. Ground Truth")
            st.json(ground_truth)
            
            if not is_valid and error_msg:
                st.error(f"Error: {error_msg}")

        st.divider()

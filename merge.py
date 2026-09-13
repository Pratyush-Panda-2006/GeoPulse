import re

with open('frontend/explorer.html', 'r', encoding='utf-8') as f:
    main_text = f.read()

with open('friend_branch_temp/explorer.html', 'r', encoding='utf-8') as f:
    friend_text = f.read()

# 1. Replace model-selector
m_model = re.search(r'<select.*?id=\"model-selector\".*?</select>', main_text, re.DOTALL)
if m_model:
    friend_text = re.sub(r'<select.*?id=\"model-selector\".*?</select>', m_model.group(0), friend_text, flags=re.DOTALL)

# 2. Replace demo-selector
m_demo = re.search(r'<select.*?id=\"demo-selector\".*?</select>', main_text, re.DOTALL)
if m_demo:
    friend_text = re.sub(r'<select.*?id=\"demo-selector\".*?</select>', m_demo.group(0), friend_text, flags=re.DOTALL)

# 3. Add analyze button back in the side panel. Where was it in main?
m_analyze_div = re.search(r'<!-- AI Interpretation Workflow -->.*?</div>\s+</div>', main_text, re.DOTALL)
if m_analyze_div:
    # insert it before "<!-- Process Action -->" in friend
    friend_text = friend_text.replace('<!-- Process Action -->', m_analyze_div.group(0) + '\n                        <!-- Process Action -->')

# 4. In JS, we need to add back the threshold listener and analyzeWithOmni
# Let's just replace the whole JS block with main's JS block, BUT add the GSAP animations if any.
# Wait, friend's JS has GSAP. Let's just append the threshold logic and analyzeWithOmni to friend's JS.
# Actually, wait, let's extract processImage from main_text and replace processImage in friend_text, 
# because processImage in friend might not use threshold values!

m_process = re.search(r'async function processImage\(\) \{.*?\n            \}', main_text, re.DOTALL)
if m_process:
    friend_text = re.sub(r'async function processImage\(\) \{.*?\n            \}', m_process.group(0), friend_text, flags=re.DOTALL)

m_omni = re.search(r'async function analyzeWithOmni\(\) \{.*?\n            \}', main_text, re.DOTALL)
if m_omni:
    friend_text = friend_text.replace('async function processImage()', m_omni.group(0) + '\n\n            async function processImage()')

# Add threshold logic to script
threshold_logic = '''
            const modelSelector = document.getElementById('model-selector');
            const thresholdSlider = document.getElementById('threshold');
            const thresholdValue = document.getElementById('threshold-value');
            if(modelSelector && thresholdSlider && thresholdValue) {
                modelSelector.addEventListener('change', (e) => {
                    const model = e.target.value;
                    if (model === 'snunet_cd_sar') {
                        thresholdSlider.value = 0.85;
                    } else if (model === 'changeformer_v6_optical') {
                        thresholdSlider.value = 0.50;
                    }
                    thresholdValue.innerText = Number(thresholdSlider.value).toFixed(2);
                });
            }
'''
friend_text = friend_text.replace('// --- Interaction & Loading Logic ---', '// --- Interaction & Loading Logic ---' + threshold_logic)

with open('frontend/explorer.html', 'w', encoding='utf-8') as f:
    f.write(friend_text)
print('Done parsing and merging explorer.html')

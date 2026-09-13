import re
with open('friend_branch_temp/studio.html', 'r', encoding='utf-8') as f:
    text = f.read()

fallback_regex = re.compile(r'// Fallback imagery if store has no data.*?t1Bg\.style\.backgroundImage', re.DOTALL)
replacement = '''// Real data check
            if (!previews || !previews.t1 || !previews.t2 || !metadata) {
                // Show empty/no-selection state
                const canvas = document.getElementById('studio-canvas');
                if (canvas) {
                    canvas.innerHTML = '<div class="flex items-center justify-center w-full h-full bg-[#0a0a0a]"><span class="text-outline font-mono tracking-widest uppercase">NO ACTIVE INFERENCE DATA</span></div>';
                }
                document.querySelectorAll('.telemetry-value').forEach(el => el.innerText = '--');
                return;
            }
            
            t1Bg.style.backgroundImage'''

new_text = fallback_regex.sub(replacement, text)

nemotron_match = re.search(r'document\.getElementById\(\'nemotron-analysis\'\)\.innerHTML = .*?;', new_text, re.DOTALL)
if nemotron_match:
    print('Found nemotron block')
    nem_replacement = '''const nemotronAnalysis = document.getElementById('nemotron-analysis');
            if (nemotronAnalysis && metadata.omni_interpretation) {
                nemotronAnalysis.innerHTML = <div class="text-on-surface-variant mb-4 font-mono leading-relaxed"></div>;
            } else if (nemotronAnalysis) {
                nemotronAnalysis.innerHTML = <div class="text-outline font-mono opacity-50">[NO AI INTERPRETATION GENERATED]</div>;
            }'''
    new_text = new_text.replace(nemotron_match.group(0), nem_replacement)

with open('frontend/studio.html', 'w', encoding='utf-8') as f:
    f.write(new_text)
print('Updated frontend/studio.html')

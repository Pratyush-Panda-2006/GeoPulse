import requests, json

print('Testing ChangeFormerV6 upload...')
url = 'http://127.0.0.1:8000/api/v1/detect/upload'
files = {
    'image_t1': ('t1.png', open(r'd:\Projects\border surv\models\ChangeFormer\samples_LEVIR\sample_1\T1.png', 'rb'), 'image/png'),
    'image_t2': ('t2.png', open(r'd:\Projects\border surv\models\ChangeFormer\samples_LEVIR\sample_1\T2.png', 'rb'), 'image/png')
}
data = {
    'model_name': 'changeformer_v6',
    'threshold': 0.95,
    'min_region_area_px': 100
}
try:
    res = requests.post(url, files=files, data=data)
    if not res.ok:
        print('Failed upload:', res.text)
    else:
        data = res.json()
        print('Upload success! Found regions:', len(data['regions']))
        
        if len(data['regions']) > 0:
            high_conf = [r for r in data['regions'] if r['mean_change_prob'] >= 0.7]
            print('High confidence regions:', len(high_conf))
            
            interpret_payload = {
                't1_base64': data['t1_preview_base64'],
                't2_base64': data['t2_preview_base64'],
                'regions': high_conf
            }
            print('Testing Interpret...')
            ires = requests.post('http://127.0.0.1:8000/api/v1/detect/interpret', json=interpret_payload)
            if not ires.ok:
                print('Failed interpret:', ires.text)
            else:
                print('Interpret success!')
                print(json.dumps(ires.json(), indent=2))
except Exception as e:
    print(e)

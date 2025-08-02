#!/usr/bin/env python3
import os
import shutil
import json
import sys
from glob import glob

# --- CONFIG ---
L2D_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(L2D_ROOT, '..'))
L2D_MODELS_DIR = os.path.join(PROJECT_ROOT, 'live2d-models')
MODEL_DICT_PATH = os.path.join(PROJECT_ROOT, 'model_dict.json')

# --- UTILS ---
def safe_mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def copy_if_exists(src, dst):
    if os.path.exists(src):
        shutil.copy2(src, dst)

def get_model_name(folder):
    # Use folder name as model name
    return os.path.basename(os.path.normpath(folder)).lower().replace(' ', '_')

def find_file(folder, exts):
    for ext in exts:
        files = glob(os.path.join(folder, f'*{ext}'))
        if files:
            return files[0]
    return None

def collect_files(folder, subdir, exts):
    result = []
    path = os.path.join(folder, subdir)
    if os.path.exists(path):
        for ext in exts:
            result.extend(glob(os.path.join(path, f'*{ext}')))
    return result

def main():
    if len(sys.argv) != 2:
        print('Usage: import_live2d_model.py <path-to-live2d-folder>')
        sys.exit(1)
    src_folder = os.path.abspath(sys.argv[1])
    model_name = get_model_name(src_folder)
    dst_folder = os.path.join(L2D_MODELS_DIR, model_name)
    safe_mkdir(dst_folder)
    # Subfolders
    exp_dir = os.path.join(dst_folder, 'expressions')
    mot_dir = os.path.join(dst_folder, 'motions')
    tex_dir = os.path.join(dst_folder, f'{model_name}.4096')
    safe_mkdir(exp_dir)
    safe_mkdir(mot_dir)
    safe_mkdir(tex_dir)
    # Copy moc3/model3/physics3/cdi3
    moc3 = find_file(src_folder, ['.moc3'])
    model3 = find_file(src_folder, ['.model3.json', '.model.json'])
    physics3 = find_file(src_folder, ['.physics3.json', '.physics.json'])
    cdi3 = find_file(src_folder, ['.cdi3.json'])
    copy_if_exists(moc3, os.path.join(dst_folder, os.path.basename(moc3))) if moc3 else None
    copy_if_exists(model3, os.path.join(dst_folder, os.path.basename(model3))) if model3 else None
    copy_if_exists(physics3, os.path.join(dst_folder, os.path.basename(physics3))) if physics3 else None
    copy_if_exists(cdi3, os.path.join(dst_folder, os.path.basename(cdi3))) if cdi3 else None
    # Copy textures
    for tex in collect_files(src_folder, f'{model_name}.4096', ['.png']):
        copy_if_exists(tex, os.path.join(tex_dir, os.path.basename(tex)))
    # Copy expressions
    for exp in collect_files(src_folder, '', ['.exp3.json', '.exp.json']):
        copy_if_exists(exp, os.path.join(exp_dir, os.path.basename(exp)))
    # Copy motions
    for mot in collect_files(src_folder, '', ['.motion3.json', '.mtn']):
        copy_if_exists(mot, os.path.join(mot_dir, os.path.basename(mot)))
    # --- Generate model3.json in mao_pro style ---
    model_json = {
        "Version": 3,
        "FileReferences": {
            "Moc": os.path.basename(moc3) if moc3 else '',
            "Textures": [os.path.join(f'{model_name}.4096', os.path.basename(t)) for t in glob(os.path.join(tex_dir, '*.png'))],
            "Physics": os.path.basename(physics3) if physics3 else '',
            "DisplayInfo": os.path.basename(cdi3) if cdi3 else '',
            "Expressions": [
                {"Name": os.path.splitext(os.path.basename(f))[0], "File": f"expressions/{os.path.basename(f)}"}
                for f in glob(os.path.join(exp_dir, '*.exp3.json')) + glob(os.path.join(exp_dir, '*.exp.json'))
            ],
            "Motions": {},
            "Pose": "",
            "DisplayInfo": os.path.basename(cdi3) if cdi3 else ''
        },
        "Groups": [
            {"Target": "Parameter", "Name": "LipSync", "Ids": ["ParamMouthOpenY"]},
            {"Target": "Parameter", "Name": "EyeBlink", "Ids": ["PARAM_EYE_L_OPEN", "PARAM_EYE_R_OPEN"]}
        ],
        "HitAreas": []
    }
    with open(os.path.join(dst_folder, f'{model_name}.model3.json'), 'w', encoding='utf-8') as f:
        json.dump(model_json, f, indent=2)
    # --- Update model_dict.json ---
    if os.path.exists(MODEL_DICT_PATH):
        with open(MODEL_DICT_PATH, 'r', encoding='utf-8') as f:
            model_dict = json.load(f)
    else:
        model_dict = []
    # Auto emotionMap: map first 8 expressions to basic emotions
    basic_emotions = ["neutral", "anger", "joy", "sadness", "surprise", "smirk", "fear", "disgust"]
    expressions = model_json['FileReferences']['Expressions']
    emotion_map = {emo: i for i, emo in enumerate(basic_emotions) if i < len(expressions)}
    # Add or update entry
    entry = {
        "name": model_name,
        "description": f"Imported model {model_name}",
        "url": f"/live2d-models/{model_name}/{model_name}.model3.json",
        "kScale": 0.5,
        "initialXshift": 0,
        "initialYshift": 0,
        "kXOffset": 1150,
        "idleMotionGroupName": "Idle",
        "emotionMap": emotion_map
    }
    # Remove old entry if exists
    model_dict = [e for e in model_dict if e.get('name') != model_name]
    model_dict.append(entry)
    with open(MODEL_DICT_PATH, 'w', encoding='utf-8') as f:
        json.dump(model_dict, f, indent=2)
    print(f"Model '{model_name}' imported! You can now set it as your default character in conf.yaml:")
    print(f"  live2d_model_name: '{model_name}'")

if __name__ == '__main__':
    main() 

with open('app/services/visual_analyzer.py') as f:
    content = f.read()
    print('mediapipe.python' in content)
    print('haarcascades' in content)
    print('import mediapipe' in content)
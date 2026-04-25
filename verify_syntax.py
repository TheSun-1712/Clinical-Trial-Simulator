import py_compile
try:
    py_compile.compile('c:/Users/rohit/Downloads/Clinical-Trial-Simulator/training/train_on_real_data.py', doraise=True)
    print("Syntax OK")
except Exception as e:
    print(e)

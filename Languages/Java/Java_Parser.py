from java_file import JavaFile

file_path = "TestProject/DataProcessor.java"
java = open(file_path, "rb").read()

file = JavaFile(java)



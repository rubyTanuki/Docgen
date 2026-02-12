from Languages.Java import JavaParser

if __name__ == "__main__":
    file_path = "Languages/Java/TestFiles/MRILib"

    parser = JavaParser(file_path)
    parser.parse()
    for file in parser.files:
        print(file)

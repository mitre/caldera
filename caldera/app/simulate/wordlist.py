import os


male_names = []
with open(os.path.join(os.path.dirname(__file__), "lists", "dist.list.male")) as f:
    for line in f.readlines():
        white_index = line.find(" ")
        male_names.append(line[:white_index].lower())

female_names = []
with open(os.path.join(os.path.dirname(__file__), "lists", "dist.list.female")) as f:
    for line in f.readlines():
        white_index = line.find(" ")
        female_names.append(line[:white_index].lower())

greek_alphabet = []
with open(os.path.join(os.path.dirname(__file__), "lists", "greek.alphabet")) as f:
    for line in f.readlines():
        greek_alphabet.append(line.strip())

animals = []
with open(os.path.join(os.path.dirname(__file__), "lists", "animals")) as f:
    for line in f.readlines():
        line = line.strip()
        if line and not line.startswith('#'):
            animals.append(line)

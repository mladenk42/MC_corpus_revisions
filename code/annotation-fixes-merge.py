# this script takes the data sent by Maris and Paloma (after fixing the ambiguities) and merges it into the main data
# specifically, first half up until B35-A55-C1-1524259025186 was done by Paloma and the rest by Maris
# the changes update the phrase.xml files
# this script copies these xml files from the Dropbox downloads over the corresponding xml files in the normalized merged data sent by yuexi

import pandas as pd
import os
import shutil

df = pd.read_csv("annotation.tsv", sep = "\t")

maris_start = 95 # this is the index where Maris' annotations start and Paloma's end

def copy_and_replace(source_path, destination_path):
    if os.path.exists(destination_path):
        print("--- FOUND DEST FILE TO REPLACE --- src and dest are:")
        print(source_path)
        print(destination_path)
    else:
        print("****** DEST FILE MISSING *************")

    if os.path.exists(destination_path):
        os.remove(destination_path)
    shutil.copy2(source_path, destination_path)

df = df.sort_values(by = ["experiment"])
print(df)

for ind, exp_name in enumerate(df.experiment):
    suffix = "-P" if ind < maris_start else "-M"
    if ind == maris_start:
        print(["*"] * 50)
    src_folder = "/media/mladen/CE34D38A34D373C5/minecraft_tmp/Minecraft_Dialogue_Corpus_Merged_2024_04_11" + suffix + "/markables/"
    src_file = src_folder + exp_name + "_phrase.xml"
    tar_file = "/home/mladen/minecraft-data-visualizer/data/Minecraft_Dialogue_Corpus_Merged_2024_04_11/markables/" + exp_name + "_phrase.xml"
    copy_and_replace(src_file, tar_file)



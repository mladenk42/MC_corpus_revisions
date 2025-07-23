# this script creates a folder full of "logs" folders from the original dataset (not all of them, only those that are included in our dataset)
# this is required as one of the inputs for the heuristic

import glob

experiment_list = glob.glob("./data/Minecraft_Dialogue_Corpus_Merged_2024_04_11/*.mmax")

experiment_list = [x.split("/")[-1].split(".")[0] for x in experiment_list]
#print(experiment_list)
#print(len(experiment_list))

log_list = glob.glob("/home/mladen/logs/*")
log_list = [x.split("/")[-1] for x in log_list]

#print(log_list)

for x in experiment_list:
    if not x in log_list:
        print("Missing")


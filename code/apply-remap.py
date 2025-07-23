import glob
import os
import json

import sys
import xml.etree.ElementTree as ET
import re
from collections import Counter

basedir = "./data/Minecraft_Dialogue_Corpus_Merged_2024_04_11"
debug_log_dir = "./export_fix/basedata/images"
basedata_dir = "./data/Minecraft_Dialogue_Corpus_Merged_2024_04_11/basedata"
new_xml_dir = "./export_fix/markables"

img_fix_file = "./fixfiles/missing_imgs.txt"

markables_folder = basedir + "/markables/"

json_data = json.load(open("/media/mladen/CE34D38A34D373C5/minecraft_tmp/new-images/remapping.json","r"))

n_updates = 0
files = glob.glob(markables_folder + "*phrase.xml")
for filename in files:
    print(filename)
    expid = filename.split("/")[-1].split("_")[0]
    print(expid)
    ET.register_namespace('', 'www.eml.org/NameSpaces/phrase')
    tree = ET.parse(filename)
    root = tree.getroot()
    for markable in root:
        if markable.get("id"):
            markable_id = markable.get("id")
            json_entries = [j for j in json_data if j["EXPERIMENT_ID"] == expid and j["MARKABLE_ID"] == markable_id]
            if len(json_entries) > 1:
                print("PANIC PANIC SOMETHING IS VERY WRONG")
            if len(json_entries) == 1:
                out_total = []
                out_total_small = []
                data = json_entries[0]
                out_img = data["IMG"]

                if isinstance(data["BLOCK_LIST"], str):
                    out_total = data["BLOCK_LIST"]
                    out_total_small = data["BLOCK_LIST"]
                else:
                    for blk in data["BLOCK_LIST"]:
                        out_id = blk["ID"]
                        out_bb = blk["BBOX"]
                        out_coords = blk["COORDS"]
                        out_color = blk["COLOR"]

                        out_for_block = []
                        out_for_block.append(out_id)
                        out_for_block.append(eval(out_bb))
                        out_for_block.append(tuple(out_coords))
                        out_for_block.append(out_color)
                        out_for_block.append(out_img)
                        out_for_block = tuple(out_for_block)
                        out_total.append(out_for_block)

                        #out_total_small.append(out_id)
                        out_total_small.append(eval(out_bb))


                    out_total = json.dumps(out_total)
                    out_total_small = ",".join([str(x) for x in out_total_small]) 


                #print(out_total)
                markable.set("object", out_total_small)
                markable.set("objectFull", out_total)
                n_updates += 1
                print("DID UPDATE!")
                #markable.set("object","lalalal")
    outfilename  = "/media/mladen/CE34D38A34D373C5/minecraft_tmp/new-phrases/" + expid + "_phrase.xml"
    #with open(outfilename, "w") as outfile:
    tree.write(outfilename, encoding="utf-8", xml_declaration = True)
    print("Written: " + outfilename)
    print("-" * 80)


print("Total updates " + str(n_updates))





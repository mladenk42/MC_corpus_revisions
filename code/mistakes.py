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


parse_whitelist = ["architect",
                   "builder",
                   "nb:architect",
                   "nb:builder", 
                   "nb:ground", 
                   "nb:builder and architect", 
                   "to_be_remove_invisible", 
                   "to_be_remove_invisible_auto", 
                   "to_be_remove_not_a_reference",
                   "to_be_remove",
                   "leave_for_future",
                   "leave_for_future_next_structure",
                   "leave_for_future_axis",
                   "leave_for_future_block_slot", # this one is not really needed but is here for copmleteness
                   "leave_for_future_slot", # this one covers the previous one because the the word "block" is removed before the parsing checks are done 
                   "leave_for_future_ground_edge",
                   "corners",
                   "target_structure"]

def parse_span(span):
    return [int(x) for x in re.findall(r"word_(\d+)",span)]

class SpanLookup:
    def __init__(self):
        self.table = {}

    def set(self, addr, val):
        if len(addr) == 1:
            self.set([addr[0],addr[0]], val)
        else:
            for i in range(addr[0], addr[1]+1):
                self.table[i] = val

    def get(self, addr):
        return self.table[addr]

    def items(self):
        return self.table.items()

def parse_phrases(experiment_id):
    tree = ET.parse(os.path.join(basedir, f"markables/{experiment_id}_phrase.xml"))
    root = tree.getroot()
    l = SpanLookup()
    result, metadata_result = {}, {}
    for markable in root:
        if markable.get("object"):
            result[parse_span(markable.get("span"))[0]] = markable.get("object")
            metadata_result[parse_span(markable.get("span"))[0]] = markable.get("id"), markable.get("min_words")
    return result, metadata_result

def parse_actions(experiment_id):
    tree = ET.parse(os.path.join(basedir, f"markables/{experiment_id}_action.xml"))
    root = tree.getroot()
    l = SpanLookup()
    for markable in root:
        l.set(parse_span(markable.get("span")), markable.get("imageview"))
    return l.table

def parse_utterances(experiment_id):
    result = {}
    tree = ET.parse(os.path.join(basedir, f"markables/{experiment_id}_utterance.xml"))
    root = tree.getroot()
    l = SpanLookup()
    for markable in root:
        l.set(parse_span(markable.get("span")), markable.get("imageview"))
    return l.table


def load_debug_log(file_path):
    full_path = os.path.join(debug_log_dir, file_path) 
    json_data = json.load(open(full_path, "r"))
    return json_data

phrase_xml_filenames = glob.glob(os.path.join(basedir, "markables/*_phrase.xml"))

phrases = []
total, good, fixed = 0, 0, 0
for xml_path in phrase_xml_filenames:
    experiment_id = xml_path.split("/")[-1].split("_")[0]
    utterances = parse_utterances(experiment_id)
    actions = parse_actions(experiment_id)

    phrase_dict, metadata_dict = parse_phrases(experiment_id)

    for dk in phrase_dict:
        word_id, object_ids = dk, phrase_dict[dk]
        markable_id, min_words = metadata_dict[dk]

        if word_id in utterances and utterances[word_id] is not None:
            image_path = utterances[word_id]
        elif word_id in actions and actions[word_id] is not None:
            image_path = actions[word_id]
        else:
            image_path = None

        total += 1

        if image_path is None:
            # try to fix:
            #print(experiment_id, word_id, object_ids, image_path)
            #print("Trying to fix")
            for line in open(img_fix_file, "r"):
                eid, wid, p  = [x.strip() for x in line.split("\t")]
                wid = int(wid)
                p = p.replace("images/","").upper().replace(".PNG",".png")
                if eid == experiment_id and wid == word_id:
                    if os.path.isfile(basedata_dir + "/images/" + p):
                        #print("Image path OK! Fix successful")
                        fixed += 1
                        image_path = p
                    else:
                        print("A markable could not be associated with an image:") 
                        print(experiment_id, word_id, object_ids, image_path)
                        print("Please edit the fixes/missing_images.txt file and add an entry for this experiment")
                        print("Work out the correct image from the _words and _actions xmls. As an exception, if the markable is architect or builder you are allowed to enter any dummy non-existent path.")
                        exit(4)

        if image_path is not None:
            good += 1
            dl_path = image_path.split("/")[-1].upper().replace(".PNG", "-debug-log.json") # debug log

            full_dl_path = os.path.join(debug_log_dir, dl_path) 
            
            if os.path.isfile(full_dl_path):
                debug_log = load_debug_log(dl_path)
            else:
                print("Debug log missing!") 
                print("Experiment is:")
                print(experiment_id, word_id, object_ids, image_path)
                if object_ids[0] in parse_whitelist: 
                    print("WARNING: The markable is architect or builder so this error will be ignored")
                    debug_log = None
                else:
                    print("The markable is not architect or builder this error can not be ignored.")
                    print("Please run the heuristic to generate a debug log for this particular experiment") 
                debug_log = None
                exit(5)
        else:
            print("Image is None somehow ...")
            print(experiment_id, word_id, object_ids, image_path)
            exit(5)

        
        phrases.append((experiment_id, word_id, object_ids, image_path, debug_log, markable_id, min_words))


print("(1) There are %d/%d cases missing the corresponding image (%d fixes successfuly applied)" % (total-good, total, fixed))
# Overview of types of problems:
# 1 Image to which the object refers to can't be determined
# 2 The object reference causes a parsing error (e.g., saying "left pillar" instead of "blocks f,g,h,j")
# 3 The object references the same block multiple times (e.g, "blocks a,b,a,d")
# 4 The object references blocks that are not in view and are missing in the coordinate mapping (this means the coordinate mapping must be augmented to include them, this requires consulting previous images)
# 5 The object references blocks that have duplicates (of the same color) in the coordinate mapping (e.g., "red a" and the coordinate mapping has two blocks that are both "red a", this requires the coordinate mapping to be fixed)
# 6 The object references blocks that have duplicates (of different colors) in the image (e.g., object is "block a" and there are both a "red a" and "green a" in the image, there is no way to tell which one was meant)

# 1 is a technical issue
# 2,3,6 are problems with phrasing of the objects
# 4,5 are problems with the heuristically generated coordinate mapping 
# I believe the annotators will be most needed for 6 and a part of 2

# We got counts for issue 1 above, we will exclude those from further counts 
phrases = [x for x in phrases if x[4] is not None]
#print(len(phrases))

# 2 Counting the parsing errors

def count_duplicates(xs):
    return len(xs) - len(set(xs))

colours = set("orange,red,blue,purple,yellow,green".split(","))

def has_tuple(xs):
    for x in xs: 
        if isinstance(x, tuple):
            return True
    return False


def has_parsing_error(xs):
    if xs[0] in parse_whitelist or xs[0] in [x.replace("_"," ") for x in parse_whitelist]:
        return False

    for x in xs:
        if isinstance(x, str) and len(x) > 1:
                print(xs[0])
                return True
    
    #print(xs, parse_whitelist)
    #if re.match("^s\d+", str(xs[0])): # 
    #    return False

    return False

def parse_colours(xs):
    result = []
    last_colour = None
    for x in xs:
        if " " in x:
            colour, address = x.split(" ", 1)
            if colour in colours:
                last_colour = colour
                x = address
        if last_colour:
            result.append((last_colour, x))
        else:
            result.append(x)
    return result


num_errors = 0
duplicates = 0

out_of_view = 0
duplicate_in_cm = 0
duplicate_in_image = 0

skipped_because_whitelist = 0

def get_best_letter(sl):
    best_letter, best_score = "!", 1000000
    for letter, score in sl:
        if score < best_score:
            best_letter, best_score = letter, score
    return best_letter


remappings_folder = "/media/mladen/CE34D38A34D373C5/minecraft_tmp/new-images/"
remapping = []
for experiment_id, word_id, object_ids, image_path, debug_log, markable_id, min_words in phrases:

    orig_object_ref = object_ids
    object_ref = object_ids.replace("_", " ")
    object_ref = re.sub("blocks?\s*","", object_ref)
    object_ref = re.split(r",\s*",object_ref)
    object_ref = parse_colours(object_ref)
    #if has_tuple(object_ref):
    #    colour_mentions +=1

    if has_parsing_error(object_ref):
        num_errors += 1
        print(orig_object_ref,"\t", image_path, "\t", markable_id)
    else:
    #   block_counts.append(len(object_ref))        
        out_dict = {}
        out_dict["IMG"] = image_path.split(".")[0].upper() + ".png"
        out_dict["IMG"] = out_dict["IMG"].split("/")[-1]
        out_dict["EXPERIMENT_ID"] = experiment_id
        out_dict["MARKABLE_ID"] = markable_id

        if object_ref[0] in parse_whitelist:
            skipped_because_whitelist += 1
            out_dict["BLOCK_LIST"] = object_ref[0]
            remapping.append(out_dict)
            continue
        #if re.match("^s\d+", str(object_ref[0])):
        #    print("ATTENTION: " + object_ref[0])
        #    continue
         
        visible_blocks = [x[0] for x in debug_log["block_out_of_view"] if x[1] == False]

        detected2crds = {}
        detected_blocks = []
        #print("---")
        for block, scorelist in debug_log["block_letter_scores"]:
            if block in visible_blocks:
                crds = block[0]
                colour = block[1]
                letter = get_best_letter(scorelist)
                detected_block = (colour, letter)
                detected_blocks.append(detected_block)                
                #if detected_block[1] == ("m"):
                #    print(crds)
                #if detected_block in detected2crds:
                #    print("OH DEAR")
                #    print(detected_block)
                #    print(crds)
                detected2crds[detected_block] = crds

 
        coords2bb = {}
        for coordcolor, bb in debug_log["mask_bbox_for_block"]:
            crds = tuple(coordcolor[0])
            coords2bb[crds] = bb
        #print("------------------------------------------------------------------------")
        #print("Image: " + image_path)
        #print("Referenced blocks:")
        #print(object_ref)
        #print("Detected blocks:")
        #print(detected_blocks)

        has_oov = False
        has_dup_cm = False
        has_dup_img = False
        out_dict["BLOCK_LIST"] = []
        for block in object_ref:
            resolved_color, resolved_coords = None, None
            if isinstance(block, tuple):
                if block not in detected_blocks:
                    has_oov = True
                if detected_blocks.count(block) > 1:
                    has_dup_cm  = True
                    #print("--------------------")
                    #print("Duplicates in coordinate mapping:")
                    #print(object_ref)
                    #print(experiment_id, word_id, object_ids, image_path)
                    #print(duplicates_curr)
                    #print("--------------------")
                    #print(block)
                    #print(detected_blocks)
                    #print(detected2crds)
                    #print("PANIC PANIC")
                    #exit()
                elif detected_blocks.count(block) == 1:
                    resolved_color = block[0]
                    resolved_coords = tuple(detected2crds[block])
                    
            else:
                if block not in [x[1] for x in detected_blocks]:
                    has_oov  = True 
                    #print("-------------------------------")
                    #print("OOV problem")
                    #print(block)
                    #print("-------------------------------")
                letter_blocks = [x for x in detected_blocks if x[1] == block]
                if len(letter_blocks) != len(set(letter_blocks)): # this means there are duplicates of that letter with the same color - [(red,a), (red,a),(blue,a)]
                   has_dup_cm = True
                   #print("--------**** ------------")
                   #print("Duplicates in coordinate mapping:")
                   #print(object_ref)
                   #print(experiment_id, word_id, object_ids, image_path)
                   #print(duplicates_curr)
                   #print("--------------------")
                   #print(block)
                   #print(detected_blocks)
                   #print(detected2crds)
                   #print("ALARM ALARM!")
                   #exit()
                if len(set(letter_blocks)) > 1: # this means there are duplicates of that letter with different colors - [(red,a), (blue,a)]
                    #print("--------------------")
                    #print("Duplicates in img reference.")
                    #print(object_ref)
                    #print(experiment_id, word_id, object_ids, image_path)
                    #print(duplicates_curr)
                    #print("--------------------")
                    #exit()
                    has_dup_img = True
                elif len(set(letter_blocks)) == 1: # THIS CONDITION SHOULD NOT BE REQUIRED IF THE CM IS FIXED TODO TODO 
                    block_full = list(set(letter_blocks))[0]
                    resolved_color = block_full[0]
                    resolved_coords = tuple(detected2crds[block_full])

            if resolved_color is not None and resolved_coords is not None:
                # parse
                block_dict = {}
                block_dict["OLD_ID_PARSED"] = block
                block_dict["COLOR"] = resolved_color
                block_dict["COORDS"] = resolved_coords
                # bounding box (from json)
                block_dict["BBOX"] = coords2bb[resolved_coords]
                # new id (from new coords file)
                coord_file_name = image_path.split("/")[-1]
                coord_file_name = coord_file_name.upper()
                coord_file_name = coord_file_name.replace(".PNG", "-new-ids.json")
                coord_file_name = "/media/mladen/CE34D38A34D373C5/minecraft_tmp/new-images/" + coord_file_name
                coords_new = json.load(open(coord_file_name, "r"))["c2id"]
                coords_new_dict = dict(zip([tuple(x[0]) for x in coords_new], [x[1] for x in coords_new]))
                block_dict["ID"] = coords_new_dict[block_dict["COORDS"]][0]
                out_dict["BLOCK_LIST"].append(block_dict)
            
        # add to overall data for this markable
        remapping.append(out_dict)


        # if any of the blocks in the object has a problem with count that object as having the problem
        out_of_view += 1 if has_oov else 0
        duplicate_in_cm += 1 if has_dup_cm else 0
        duplicate_in_image += 1 if has_dup_img else 0


        if has_dup_img:
            step = image_path.split("_")[1].split(".")[0]
            #print("\t".join([str(x) for x in [experiment_id, step, object_ids, min_words, word_id, markable_id, image_path]]))
        
        #print(f"has_oov = {has_oov}")
        #print(f"has_dup_cm = {has_dup_cm}")
        #print(f"has_dup_img = {has_dup_img}")

        duplicates_curr = count_duplicates(object_ref)
        duplicates += duplicates_curr
        if duplicates_curr > 0:
            pass
            #print("--------------------")
            #print("Duplicates in obj. reference.")
            #print(object_ref)
            #print(experiment_id, word_id, object_ids, image_path)
            #print(duplicates_curr)
            #print("--------------------")
            #exit()

    #objects += 1


print(f"(2) There are {num_errors} parsing errors ({skipped_because_whitelist} skipped because they are special entities).")
print(f"(3) There are {duplicates} duplicates in the obj. reference text.")

print(f"(4) There are {out_of_view} cases of out of view blocks referenced (in addition to those marked invisible in step 2).")
print(f"(5) There are {duplicate_in_cm} cases where a block reference is ambiguous in the coordinate mapping.")
print(f"(6) There are {duplicate_in_image} cases where a block reference is ambiguous in the image. ")

# write remapping json to disk (it has one entry for each referenced markable)
final_outfile_name = "/media/mladen/CE34D38A34D373C5/minecraft_tmp/new-images/remapping.json"
print(final_outfile_name)
print(len(remapping))
json.dump(remapping, open(final_outfile_name, "w"))
print("Written output to: " + final_outfile_name)

 











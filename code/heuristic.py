import main
import sys
import os
import cv2
import copy
import data
from spacy.lang.en import English
from spacy.pipeline import SentenceSegmenter
import re
import spacy
from lxml import etree
from lxml.builder import E
from app import App
import shutil
import logging
from distutils.dir_util import copy_tree
import neuralcoref
from tqdm import tqdm
import string
import numpy as np
import json

import time

from util import image_mae, mae

from iglu_dataset_scripts import MultiturnDataset, SingleturnDataset
from iglu_dataset_scripts.task import Tasks
import iglu

# create logger
import logging
logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)


REQ_PYTHON = (3,7)
ACTUAL_PYTHON = (sys.version_info.major, sys.version_info.minor)
if REQ_PYTHON != ACTUAL_PYTHON:
    sys.exit("Python %s.%s or later required.\n" % REQ_PYTHON)
    # if you go later than this version spacy doesn't work
    # if you go earlier pygame doesn't work

path = "../selected-data"

#spacy.load('en_core_web_sm')
#nlp = English()

def split_on_breaks(doc):
    print("split_on_breaks: ", type(doc), doc)
    print("user data: ", doc.user_data)
    start = 0
    seen_break = False
    for word in doc:
        if seen_break:
            yield doc[start:word.i-1]
            start = word.i
            seen_break = False
        elif word.text == '@SentBoundary@':
            seen_break = True
    if start < len(doc):
        yield doc[start:len(doc)]


def _word_span(start, end):
    if start == end:
        return f"word_{start}"
    else:
        return f"word_{start}..word_{end}"

def render_xml(tree, **options):
    xml_config = {"pretty_print":True, "xml_declaration":True, "encoding":"UTF-8"}
    xml_config.update(options)
    return etree.tostring(tree, **xml_config)

def write_xml(xml, path):
    with open(path, "wb") as fh:
        fh.write(xml)

def base_dir(dir_path):
    return os.path.join("export_fix", dir_path)

for dir_path in ["markables", "common", "basedata","basedata/images"]:
    final_path = base_dir(dir_path)
    if not os.path.exists(final_path):
        os.makedirs(final_path)

def summarize_block(block):
    (x,y,z), color = block
    return f"{color}@{x},{y},{z}"

def summarize_blocks(blocks):
    return "; ".join(map(summarize_block, blocks))

identity = lambda *x: x

class Doc:
    def __init__(self, name):
        self.words = []
        self.name = name
        self.sentences = []
        self.actions = 0
        self.speaker = []
        self.doc = ""
        self.processed_doc = None
        self.images = []
        #self.meta_word_ids = []
        self.char_sentence_boundaries = []

    def words_by_type(self, has_action):
        return [word for word, is_action in self.words if is_action == has_action]

    def add_sentence(self, speaker, sentence, image, is_action):
        process_sentence = identity if is_action else self.tokenizer
        tokens = [(x, is_action) for x in process_sentence(sentence)]
        sentence_start = len(self.words)
        self.words.extend(tokens)
        self.speaker.append(speaker)
        if not is_action:
            self.doc += sentence + " "
            self.char_sentence_boundaries.append(len(self.doc))
        else:
            self.actions += 1
        self.sentences.append(((sentence_start, len(self.words)-1), is_action, self.actions))
        self.images.append(image)
    
    #def add_action(self, actions, image):
    #    tokens = [(x, True) for x in actions]
    #    sentence_start = len(self.words)
    #    self.words.extend(tokens)
    #    self.actions.append((sentence_start, len(self.words)-1))
    #    self.images.append(image)
    #    self.speaker.append("Builder")

    def sentence_break(self, doc):
        boundaries = self.char_sentence_boundaries[:]
        txt = ""
        start = 0
        seen_break = False
        for word in doc:
            txt += word.text_with_ws
            if len(txt) > boundaries[0]:
                boundaries = boundaries[1:]
                print("*** sentence break", len(txt), boundaries, start, word.i, doc[start:word.i])
                yield doc[start:word.i]
                start = word.i
            #if seen_break:
            #    yield doc[start:word.i-1]
            #    start = word.i
            #    seen_break = False
            #elif word.text == '@SentBoundary@':
            #    seen_break = True
        #if start < len(doc):
        #    yield doc[start:len(doc)]
        if start < len(doc):
            yield doc[start:]

    def tokenizer(self, string):
        nlp = spacy.load('en')
        return list(map(str, nlp.tokenizer(string)))

    def process(self):
        print("*** doc", self.doc)
        #sbd = SentenceSegmenter(nlp.vocab, strategy=split_on_breaks)
        nlp = spacy.load('en')
        sbd = SentenceSegmenter(nlp.vocab, strategy=self.sentence_break)
        nlp.add_pipe(sbd, first=True)
        neuralcoref.add_to_pipe(nlp)
        if not self.processed_doc:
            self.processed_doc = nlp(self.doc)
            print("**** sentences", list(self.processed_doc.sents))

    @property
    def meta_word_ids(self):
        return [idx for idx, (_, is_action) in enumerate(self.words) if is_action]

    def advance_meta_word_ids(self, word_id):
        return word_id + len([wid for wid in self.meta_word_ids if word_id >= wid])
        #while word_id in self.meta_word_ids:
        #    word_id += 1
        #return word_id

    def word_span(self, start, end, meta=False):
        if not meta:
            start = self.advance_meta_word_ids(start)
            end = self.advance_meta_word_ids(end)
        return _word_span(start, end)

    def export_phrases(self):
        self.process()
        markables = []
        default_props = dict(gram_fnc="unmarked", gender="unspecified", reference="new", disagreement_type="no_disagreement", generic="generic-no", related_object="no",  number="undersp-num", ambiguity="unambiguous", person="per1",  category="person", ref_type="phrase")
        seen_spans = set()
        for cluster in self.processed_doc._.coref_clusters:
            #print(cluster)
            last_markable_id=None
            for span in cluster:
                markable = default_props.copy()
                #print("*** ", span, (span.start, span.end))
                markable_id = f"markable_{len(markables)}"
                seen_spans.add((span.start, span.end))
                if last_markable_id:
                    markable["reference"] = "old"
                markable["span"] = self.word_span(span.start,span.end-1)
                if last_markable_id:
                    markable["single_phrase_antecedent"] = last_markable_id
                    markable["phrase_antecedent"] = "single_phrase"
                markables.append(markable)
                last_markable_id = markable_id
        #print(self.meta_word_ids)
        for chunk in self.processed_doc.noun_chunks:
            span = (chunk.start, chunk.end)
            #print("****NP chunk: ", chunk, chunk.start, chunk.end)
            if span not in seen_spans:
                markable = default_props.copy()
                markable_id = f"markable_{len(markables)}"
                markable["span"] = self.word_span(span[0], span[1]-1)
                markable["min_words"] = chunk.root.text
                markable["min_ids"] = self.word_span(chunk.root.i, chunk.root.i)
                markables.append(markable)
        phrase_xml_string = self.export_markables("phrase", markables)
        write_xml(phrase_xml_string, base_dir(f"markables/{self.name}_phrase.xml"))

    
    @classmethod
    def from_experiment(cls, experiment, path):
        print(f"Experiment: {experiment}")
        doc = cls(experiment)
        chat_points = [(p['chat'], main.convert_point(p)) for p in data.load(experiment, path) if main.is_valid_point(p)]
        points = [x[1] for x in chat_points]
        #print(points)
        #return

        overall_chat_points_processed = 0
        overall_duplicates = 0
        for point_idx, (chat, point) in enumerate(tqdm(chat_points, position=0, desc=f"Experiment {experiment}")):
            output_filename = base_dir(f"basedata/images/{experiment}_{point_idx}-debug-log.json")
            if os.path.isfile(output_filename):
                print("Skipping %s because it is already done" % output_filename)
                continue
            skip_this_step = False
            #if point_idx < 46:
            #    continue
            party, message = None, None
            #print("CAMERA IN MMAX")
            #print(points[point_idx])
            app = App(points, point_idx)
            image_filename = base_dir(f"basedata/images/{experiment}_{point_idx}.png")
            #app.run_to_file(image_filename)
            #app.run_to_file("/home/mladen/tmp-orig-gen.png")
            app.letter_coord_to_file(base_dir(f"basedata/images/{experiment}_{point_idx}.json"))
            if chat:
                party, message = chat.split(" ", 1)
                doc.add_sentence(party.strip("<>"), message, f"images/{experiment}_{point_idx}.png", False)
            summary = []
            if point['world_added']:
                summary.append("added " + summarize_blocks(point['world_added']))
            if point['world_removed']:
                summary.append("removed " + summarize_blocks(point['world_removed']))
            summary = " and ".join(summary)
            if summary:
                doc.add_sentence("Builder", summary, f"images/{experiment}_{point_idx}.png", True)
                #doc.add_action([summary], image_filename)
            
            #print(" --- STARTING INNER LOOP AGAIN ---")

            json_data = {}
            json_data["candidate_list_for_block"] = {}
            json_data["mask_weight_for_block"] = {}
            json_data["block_out_of_view"] = {}
            json_data["block_letter_scores"] = {}
            json_data["mask_bbox_for_block"] = {}
 
            for app_idx, perm in enumerate(app.app_permutations()):
                block_list = perm
                break
            json_data["block_list"] = block_list
            #if len(block_list) < 2: 
            #    continue
            result = {}

            #shutil.copy(f"/home/mladen/minecraft-data-visualizer/data/Minecraft_Dialogue_Corpus_Merged_2024_04_11/basedata/images/{experiment}_{point_idx}.png","/home/mladen/tmp-orig.png")
            original_export = cv2.imread(f"/home/mladen/minecraft-data-visualizer/data/Minecraft_Dialogue_Corpus_Merged_2024_04_11/basedata/images/{experiment}_{point_idx}.png")
            for coords, color in block_list:
                ##print(" *** STARTING FOR COORD ***")
                #print(coords)
                color_count = len([x for x in block_list if x[1] == color])
                letter_candidates = (string.ascii_letters + string.digits)[0:color_count]
                json_data["candidate_list_for_block"][(coords, color)] = letter_candidates
                best_letter, best_error = None, 1000000
                skip_this_block = False
                letter_scores = []

                for letter_candidate in letter_candidates:
                    if skip_this_block: # skips invisible blocks (this is caught in the first iteration of the loop)
                        continue
                    #print("TESTING LETTER " + str(letter_candidate))
                    app.force_letter_for_coord = letter_candidate, coords
                    app.outside_coord_to_letter = None # just in case
                    app.dont_ignore_block = coords
                    new_points = copy.deepcopy(points)
                    new_points[point_idx]['world'] = block_list # the above will cause app to internally modify how the letters are generated
                    app.change_data(new_points)
                    image_filename = base_dir(f"basedata/images/{experiment}_{point_idx}.png")
                    #original_export = cv2.imread(f"/Users/chrismadge/annotated-minecraft-export/Minecraft_Dialogue_Corpus_Maris_2024_03_01/basedata/images/{experiment}_{point_idx}.png")
                    
                    # THIS SHOULD NOT HAPPEN?
                    #if original_export is None:
                    #    skip_this_step = True
                    #    break # the loop over letters

                    im_buffer = app.image_buffer()
                    #app.run_to_file("/home/mladen/tmp.png")
                    #cv2.imshow("image", original_export)
                    #cv2.waitKey(0)
                    #exit()
                    # make binary mask
                    rgbmax = np.max(im_buffer, axis=2)
                    # values are 0 - 255, if all are below 5 (arbitrary, any low value will do) we consider it a black pixel and it is masked out (mask2d has 0 there)
                    mask2dint = (rgbmax > 5.0).astype(np.int_) 
                    mask2d = mask2dint.astype(np.float32) 
                    json_data["mask_weight_for_block"][(coords, color)] = str(np.sum(mask2d))
                     
                    def get_bbox(m):
                        nz = np.nonzero(m)
                        v_coords = nz[0]
                        h_coords = nz[1]

                        if len(v_coords) == 0:
                            top, bottom = -1, -1 
                        else:
                            top = np.min(v_coords)
                            bottom = np.max(v_coords)
                        
                        if len(h_coords) == 0:
                            left, right = -1, -1
                        else:
                            left = np.min(h_coords)
                            right = np.max(h_coords)

                        return (top, bottom, left, right)


                    json_data["mask_bbox_for_block"][(coords, color)] = str(get_bbox(mask2dint))
                    if np.max(mask2d) < 0.01:
                        skip_this_block = True
                    mask3d = np.dstack([mask2d, mask2d, mask2d])
                    #cv2.imshow("image", mask2d)
                    #cv2.waitKey(0)
                    #print(np.max(mask3d))
                    #exit()
                    # mask the original image
                    original_export_masked = np.multiply(mask3d, original_export)
                    #print(original_export_masked.shape)
                    #print(original_export_masked.dtype)

                    # TMP DEBUG
                    #print("Writing tmp image to file ...")
                    #app.run_to_file("/home/mladen/tmp.png")
                    #print("Copying reference image ...")
                    #shutil.copy(f"/home/mladen/minecraft-data-visualizer/data/Minecraft_Dialogue_Corpus_Maris_2024_03_01/basedata/images/{experiment}_{point_idx}.png","/home/mladen/tmp-orig.png")
                    #print("Finished.")

                    error = mae(im_buffer, original_export_masked)
                    letter_scores.append((letter_candidate, error))
                    #print("Obtained error: " + str(error))
                    if error < best_error:
                        best_letter, best_error = letter_candidate, error
                if skip_this_step:
                    break # the loop over blocks in this image
                json_data["block_letter_scores"][(coords, color)] = letter_scores
                if not skip_this_block:
                    result[coords] = (best_letter, color)
                    json_data["block_out_of_view"][(coords, color)] = False
                else:
                    json_data["block_out_of_view"][(coords, color)] = True

            if skip_this_step:
                continue # to the next step in the chat (the current step is being skipped)

            # check
            if len(result.values()) != len(set(result.values())):
                print("MISTAKE, WE HAVE DOUBLE ENTRIES, additional fixing needed")
                overall_duplicates += 1
                print(result)
                # TODO: extra step to resolve duplicates
                #exit()
            
            # extra step to add "-" entries for those positions that were not mentioned in the previous result since they are not visible to the camera
            #for coords, color in block_list:
            #    if coords not in result:
            #        result[coords] = ("-","green")
            #new_points = copy.deepcopy(points)
            #app.force_letter_for_coord = None
            #app.outside_coord_to_letter = result
            #app.dont_ignore_block = None
            #new_points[point_idx]['world'] = block_list
            #app.change_data(new_points)
            #image_filename = base_dir(f"basedata/images/{experiment}_{point_idx}.png")
            #original_export = cv2.imread(f"/Users/chrismadge/annotated-minecraft-export/Minecraft_Dialogue_Corpus_Maris_2024_03_01/basedata/images/{experiment}_{point_idx}.png")
            #original_export = cv2.imread(f"/home/mladen/minecraft-data-visualizer/data/Minecraft_Dialogue_Corpus_Maris_2024_03_01/basedata/images/{experiment}_{point_idx}.png")
            #im_buffer = app.image_buffer()
            #final_error = mae(im_buffer, original_export) # TODO: remember somewhere
            #app.run_to_file(image_filename)
            #app.letter_coord_to_file(base_dir(f"basedata/images/{experiment}_{point_idx}.json"))
            
            overall_chat_points_processed += 1
            
            #app.letter_coord_to_file(base_dir(f"basedata/images/{experiment}_{point_idx}.json"))

            # json doesn't allow dictionaries with tuples as keys so we store these as key, value pair lists instead
            for json_key in ["candidate_list_for_block", "mask_weight_for_block", "block_out_of_view", "block_letter_scores", "mask_bbox_for_block"]:
                json_data[json_key] = [(k, v) for k, v in json_data[json_key].items()]
            json.dump(json_data, open(base_dir(f"basedata/images/{experiment}_{point_idx}-debug-log.json"), "w"))



        print("Overall images: " + str(overall_chat_points_processed))
        print("Overall images with duplicates: " + str(overall_duplicates))
        return doc

    @classmethod
    def from_iglu_task(cls, experiment):
        doc = cls(experiment)
        #experiment_data = iglu_data[experiment]
        experiment_data = iglu.get_data(experiment)
        chat_points = []
        last_action = {"builder_position": {"x": 0, "y": 0, "z": 0, "yaw": 0, "pitch": 0, "world": []}}
        for step in experiment_data:
            actions = step['actions']
            dialog = step['dialog']
            for action in actions:
                action = {"builder_position": {\
"x": action["position"][0],\
"y": action["position"][1]+1.0,\
"z": action["position"][2],\
"yaw": action["camera"][0]-90,\
"pitch": action["camera"][1]},\
"world": action['grid'],\
"world_added": action['added'],\
"world_removed": action['removed']}
                last_action = action
                chat_points.append((dialog, action))
                dialog = ""
            if not actions:
                last_action['world_added'] = set()
                last_action['world_removed'] = set()
                chat_points.append((dialog,last_action))
        points = [x[1] for x in chat_points]
        for point_idx, (chat, point) in enumerate(chat_points):
            print(point)
            party, message = None, None
            app = App(points, point_idx)
            image_filename = base_dir(f"basedata/images/{experiment}_{point_idx}.png")
            app.run_to_file(image_filename)
            app.letter_coord_to_file(base_dir(f"basedata/images/{experiment}_{point_idx}.json"))
            if chat:
                party, message = chat.split(" ", 1)
                doc.add_sentence(party.strip("<>"), message, f"images/{experiment}_{point_idx}.png", False)
            summary = []
            if point['world_added']:
                summary.append("added " + summarize_blocks(point['world_added']))
            if point['world_removed']:
                summary.append("removed " + summarize_blocks(point['world_removed']))
            summary = " and ".join(summary)
            if summary:
                doc.add_sentence("Builder", summary, f"images/{experiment}_{point_idx}.png", True)
                #doc.add_action([summary], image_filename)
        return doc
        

#        [for action in actions
#        "builder_position": .concat(camera), "world": 
#
#    @classmethod
#    def from_iglu_task(cls, experiment, data):
#        doc = cls(experiment)
#        colours = ["air", "blue", "green", "red", "orange", "purple", "yellow"]
#        #to_sparse = lambda xs: xs.nonzero()
#        to_sparse  = lambda xs: Tasks.to_sparse(xs)
#        convert_points = lambda xs: set([((x,  y+1, z), colours[color]) for x,y,z,color in xs])
#        builder_position = {'x': -0.894356102626326, 'y': 2.58873591650426, 'z': 10.440305537431149, 'yaw': 276.44794, 'pitch': 9.449905}
#        points = []
#        point_idx = 0
#        for instruction in data[experiment]:
#            for t in instruction:
#                #print("starting", instruction.starting_grid)
#                #print("starting non zero", instruction.starting_grid.nonzero())
#                target_grid = convert_points(to_sparse(t.target_grid))
#                starting_grid = convert_points(t.starting_grid)
#                print("starting grid", starting_grid)
#                points.append({"builder_position": builder_position, "world": starting_grid})
#        for instruction in data[experiment]:
#            for t in instruction:
#                party, message = None, None
#                target_grid = convert_points(to_sparse(t.target_grid))
#                starting_grid = convert_points(t.starting_grid)
#                app = App(points, point_idx)
#                image_filename = base_dir(f"basedata/images/{experiment}_{point_idx}.png")
#                app.run_to_file(image_filename)
#                summary = []
#                added = target_grid - starting_grid
#                removed = starting_grid - target_grid
#                chat = t.instruction
#                if chat:
#                    party, message = chat.split(" ", 1)
#                    doc.add_sentence(party.strip("<>"), message, f"images/{experiment}_{point_idx}.png", False)
#                if added:
#                    summary.append("added " + summarize_blocks(added))
#                if removed:
#                    summary.append("removed" + summarize_blocks(removed))
#                summary = " and ".join(summary)
#                if summary:
#                    doc.add_sentence("Builder", summary, f"images/{experiment}_{point_idx}.png", True)
#                point_idx = point_idx + 1
#        return doc
#            #print(added, removed)

    #@classmethod
           

    def export_markables(self, level, markables):
        return render_xml(E.markables(\
            *[E.markable(id=f"markable_{i}", \
                        mmax_level=level, \
                        order_id=str(i), \
                        **markable) \
                for i, markable in enumerate(markables)], \
            xmlns=f"www.eml.org/NameSpaces/{level}"), doctype='<!DOCTYPE markables SYSTEM "markables.dtd">')

    def export_utterances(self):
        #sentence_xml = E.markables(\
        #    *[E.markable(id=f"markable_{i}", \
        #                span=word_span(*sentence), \
        #                mmax_level="sentence", \
        #                imageview=self.images[i], \
        #                order_id=str(i)) \
        #        for i, sentence in enumerate(self.sentences)], \
        #    xmlns="www.eml.org/NameSpaces/sentence")
        #print("**** speaker", self.speaker)
        #print("**** actions", [x for _,x,_ in self.sentences])
        is_clarification = [speaker == "Builder" and not is_action for (_,is_action,_),speaker in zip(self.sentences, self.speaker)]
        #print("**** clarification", is_clarification)
        has_clarification = is_clarification[1:] + [False]
        #print("**** has_clarification", has_clarification)

        markables = [{"span": self.word_span(*sentence, True), 
                    "imageview":self.images[i], 
                    "participant": participant, 
                    "clarified_utterance": f"markable_{i-action_count-1}" if is_clarification[i] else "", 
                    "clarificationrequest": "unclear" if has_clarification[i] else "clear", 
                    "world_state": f"s{action_count}"} 
                    for i, (participant, (sentence, is_action, action_count)) in enumerate(zip(self.speaker,self.sentences)) if not is_action]
        print("**** markables", markables)

        #render_xml(sentence_xml, doctype='<!DOCTYPE markables SYSTEM "markables.dtd">')
        sentence_xml_string = self.export_markables("utterance", markables)
        write_xml(sentence_xml_string, base_dir(f"markables/{self.name}_utterance.xml"))

    def export_actions(self):
        #sentence_xml = E.markables(\
        #    *[E.markable(id=f"markable_{i}", \
        #                span=word_span(*sentence), \
        #                mmax_level="sentence", \
        #                imageview=self.images[i], \
        #                order_id=str(i)) \
        #        for i, sentence in enumerate(self.sentences)], \
        #    xmlns="www.eml.org/NameSpaces/sentence")

        markables = [{"span": self.word_span(*sentence, True), "imageview":self.images[i], "world_state": f"s{action_count}"} for i, (participant, (sentence, is_action, action_count)) in enumerate(zip(self.speaker,self.sentences)) if is_action]

        #render_xml(sentence_xml, doctype='<!DOCTYPE markables SYSTEM "markables.dtd">')
        sentence_xml_string = self.export_markables("action", markables)
        write_xml(sentence_xml_string, base_dir(f"markables/{self.name}_action.xml"))

    def export_words(self):
        #word_xml = E.words(\
                #*[E.word(word,id=f"word_{i}") \
                    #for i, word in enumerate(self.words)])
        words = []
        word_idx = 0
        for token, meta in self.words:
            props = {}
            if meta:
                #self.meta_word_ids.append(word_idx)
                props["meta"] = "True"
            props["id"] = f"word_{word_idx}"
            word_idx += 1
            words.append(E.word(token, **props))
        word_xml = E.words(*words)
        word_xml_string = render_xml(word_xml, doctype='<!DOCTYPE words SYSTEM "words.dtd">')
        write_xml(word_xml_string, base_dir(f"basedata/{self.name}_words.xml"))
    
    def export_base(self):
        base_xml = render_xml(E.mmax_project(\
            E.turns(),\
            E.words(f"{self.name}_words.xml"),\
            E.gestures(),\
            E.keyactions()))
        write_xml(base_xml, base_dir(f"{self.name}.mmax"))

    def use_template(self):
        copy_tree("mmax_template", base_dir(""))

    def export_common(self):
        common_paths_xml = render_xml(E.common_paths(\
            E.basedata_path("basedata/"),\
            E.schema_path("common/"),\
            E.style_path("common/"),\
            E.customization_path("common/"),\
            E.markable_path("markables/"),\
            E.views(E.stylesheet("default_style.xsl")),\
            E.annotations(E.level("$_sentences.xml", name="sentence", schemefile="sentence_scheme.xml", customization_file="sentence_customization.xml"))))
        write_xml(common_paths_xml, base_dir("common_paths.xml"))

    def export_sentence_customization(self):
        write_xml(render_xml(E.annotationscheme(E.attribute(E.value(id="value", name="value"), id="imageview",\
                            name="imageview",\
                            type="imageview"))), base_dir("sentence_scheme.xml"))

        write_xml(render_xml(E.customization(E.rule(pattern="{all}", style="handles=green"))), base_dir("common/sentence_customization.xml"))



if __name__ == "__main__":
    #dataset = MultiturnDataset(dataset_version='v1.0')
    #tasknames = iglu.get_tasknames()
    #iglu_data = iglu.get_data()
    #experiment = dataset.tasks['c116']
    #for experiment in ['c116']:#dataset.tasks.keys():
    #for task in [tasknames[8]]:
    #for task in tasknames:
    #    try:
            #if "2-c118" in task:
    #        if True:
    #            doc = Doc.from_iglu_task(task)

    path="/Users/chrismadge/minecraft/data-3-30/logs/"
    path = "/home/mladen/minecraft-data-visualizer/data/The Minecraft Dialogue Corpus -- no screenshots/The Minecraft Dialogue Corpus -- no screenshots/data-3-30/logs/logs/"
    path = "./logs/" # I copied the relevant log folders from the original dataset

    CURRENT_PROCESS = int(sys.argv[1])
    NUM_PROCESSES = int(sys.argv[2])

    print(data.experiments(path))

    N_EXPERIMENTS = len(data.experiments(path))

    iteration = 0
    for experiment in data.experiments(path):
        #print(iteration)
        #if "B1-A3-C1-1522435497386" in experiment:
        #if iteration > 1:
        #    exit()

        start_time = time.time()
        if iteration % NUM_PROCESSES == CURRENT_PROCESS: # process N does all those iterations where the remainder is N
            #print(experiment)
            doc = Doc.from_experiment(experiment, path)
        iteration += 1
        
    end_time = time.time()
    print("Overall runtime: " + str(end_time - start_time))
   
#        print(doc)
              #  doc.use_template()
              #  doc.export_utterances()
              #  doc.export_actions()
              #  doc.export_phrases()
              #  doc.export_words()
              #  doc.export_base()
              #  print(f"Task {task} done")
            #else:
            #    print(f"Task {task} not found")
        #except Exception:
        #    print(f"Task {task} failed")
#        

#
#####
#doc.export_common()
#doc.export_sentence_customization()



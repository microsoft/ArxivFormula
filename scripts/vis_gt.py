import os
import cv2
from tqdm import tqdm
from pycocotools.coco import COCO
import numpy as np

mode = "examples"
image_root = f"{mode}"
json_path = f"{mode}.json"
vis_root = f"VIS_GT/{mode}"
os.makedirs(vis_root, exist_ok=True)

coco_api = COCO(json_path)
image_ids = list(coco_api.imgs.keys())[:100]

category_id2name = {each['id'] : each['name'] for each in coco_api.dataset['categories']}
rel_category_id2name = {each['id'] : each['name'] for each in coco_api.dataset['relation_categories']}

color_map = {
    "InlineFormula": (123, 42, 221),
    "DisplayedFormulaLine": (213, 155, 91),
    "FormulaNumber": (175, 52, 129),
    "DisplayedFormulaBlock": (71, 173, 112),
    "Table": (255, 0, 0),
    "Figure": (0, 255, 255),
    "NextFormulaLine": (36, 208, 145),
    "FormulaReferenceNumber": (49, 125, 237)
}

for image_id in tqdm(image_ids):
    filename = coco_api.imgs[image_id]['file_name']
    im = cv2.imread(os.path.join(image_root, filename))
    annos = coco_api.imgToAnns[image_id]
    for anno in annos:
        if anno['category_id'] == 4:  # don't show DisplayedFormulaBlock
            continue
        segms = anno['segmentation']
        for segm in segms:
            pts = np.array(segm).reshape(-1, 2).astype(np.int32)
            cat_name = category_id2name[anno['category_id']]
            color = color_map[cat_name]
            cv2.polylines(im, [pts], True, color, 1, cv2.LINE_AA)
    for relation in coco_api.imgs[image_id]["relations"]:
        sbj_x0, sbj_y0, sbj_w, sbj_h = coco_api.anns[relation[0]]['bbox']
        sbj_xcen, sbj_ycen = sbj_x0 + sbj_w / 2, sbj_y0 + sbj_h / 2
        obj_x0, obj_y0, obj_w, obj_h = coco_api.anns[relation[1]]['bbox']
        obj_xcen, obj_ycen = obj_x0 + obj_w / 2, obj_y0 + obj_h / 2
        rel_cat_name = rel_category_id2name[relation[2]]
        color = color_map[rel_cat_name]
        cv2.arrowedLine(im, (int(sbj_xcen), int(sbj_ycen)), (int(obj_xcen), int(obj_ycen)), color, 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(vis_root, filename), im)

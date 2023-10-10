# ArxivFormula Details

## Annotation Format

We use the standard COCO-style annotation format for formula entity detection. There are 6 predefined page object categories, i.e., **Inline Formula**, **Displayed Formula Line**, **Formula Number**, **Displayed Formula Block**, **Table** and **Figure**. Note that the annotations of the tables and figures are not used in our paper. Moreover, there are 2 predefined formula relationships, i.e., **Next Fomrula Line** and **Formula Reference Number**. To include formula relationships in the COCO-style JSON file, we add a new field called **"relations"** in the **"images"** field. In this field, we store a list of relationships, where each relationship is represented by an object containing the subject annotation ID (sbj_id), object annotation ID (obj_id), and relationship category ID (rel_id) Additionally, we add a new field called **"relation_categories"** to store information about the relationship categories.

```python
categories = [
    {'supercategory': 'formula', 'id': 1, 'name': 'InlineFormula', 'isthing': 1},
    {'supercategory': 'formula', 'id': 2, 'name': 'DisplayedFormulaLine', 'isthing': 1},
    {'supercategory': 'formula', 'id': 3, 'name': 'FormulaNumber', 'isthing': 1},
    {'supercategory': 'formula', 'id': 4, 'name': 'DisplayedFormulaBlock', 'isthing': 1},
    {'supercategory': 'table', 'id': 5, 'name': 'Table', 'isthing': 1},
    {'supercategory': 'figure', 'id': 6, 'name': 'Figure', 'isthing': 1},
]

relation_categories = [
    {'supercategory': 'formula', 'id': 1, 'name': 'NextFormulaLine', 'isthing': 1},
    {'supercategory': 'formula', 'id': 2, 'name': 'FormulaReferenceNumber', 'isthing': 1},
]


dataset = {  
  "info": {...},  
  "licenses": [...],  
  "images": [  
    {  
      "id": 1,  
      "file_name": "image_name.jpg",  
      "relations": [(sbj_id, obj_id, rel_id), ...]  
    },  
    ...  
  ],  
  "annotations": [  
    {  
      "id": 1,  
      "image_id": 1,  
      "category_id": 1,  
      "bbox": [50, 30, 150, 200],
      "segmentation": [[50, 30, 200, 30, 200, 230, 50, 230]]
    },  
    ...  
  ],  
  "categories": categories,
  "relation_categories": relation_categories,
} 
```

## Random Distortation

We utilize some standard 2D image distortion techniques, including scale-rotate-translate and barrel distortion, to produce distorted document images for multi-oriented and arbitrary-shaped formula entity detection. Specifically, we apply a random rotation to training images within the range of $[-45\degree, 45\degree ]$, and we use barrel distortion to create distorted document images. You can use following script to distort the dataset.

```bash
python scripts/random_distortation.py
```
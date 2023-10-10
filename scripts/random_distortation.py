import os
import json
import random
import numpy as np
import cv2
from detectron2.data import transforms as T
from pycocotools.coco import COCO
from p_tqdm import p_map


def interpolater_segmentation(annos):
    for idx, anno in enumerate(annos):
        new_segm = []
        for seg in anno['segmentation']:
            point_num = len(seg) // 2
            num = len(seg)
            inserted_seg = []
            for i in range(point_num):
                x0, y0, x1, y1 = seg[(2*i) % num], seg[(2*i + 1) % num], seg[(2*i + 2) % num], seg[(2*i + 3) % num]
                inter_num = 3  # insert 3 points for each edge
                xs = np.linspace(x0, x1, inter_num, False)
                ys = np.linspace(y0, y1, inter_num, False)
                inserted_seg.extend(np.stack((xs, ys), axis=1).reshape(-1).tolist())
            new_segm.append(inserted_seg)
        anno['segmentation'] = new_segm
    return annos


class RotationTransform(T.RotationTransform):
    def apply_image(self, img, interp=None):
        """
        img should be a numpy array, formatted as Height * Width * Nchannels
        """
        if len(img) == 0 or self.angle % 360 == 0:
            return img
        assert img.shape[:2] == (self.h, self.w)
        interp = interp if interp is not None else self.interp
        return cv2.warpAffine(img, self.rm_image, (self.bound_w, self.bound_h), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255))


class DistortionTransform(T.Transform):
    def __init__(self, param, shape):
        self.param = param
        self.shape = shape
    
    def apply_image(self, img):
        H, W, C = img.shape
        cx, cy = self.param['cx'], self.param['cy']
        fx, fy = self.param['fx'], self.param['fy']
        k1, k2, k3, p1, p2 = self.param['k1'], self.param['k2'], self.param['k3'], self.param['p1'], self.param['p2']
        Xs, Ys = np.meshgrid(np.arange(W), np.arange(H))
        x = (Xs - cx) / fx
        y = (Ys - cy) / fy
        r = x ** 2 + y ** 2
        # distortion
        newx = x * (1 + k1 * r + k2 * r ** 2 + k3 * r ** 3) + 2 * p1 * x * y + p2 * (r ** 2 + 2 * x * x)
        newy = y * (1 + k1 * r + k2 * r ** 2 + k3 * r ** 3) + 2 * p2 * x * y + p1 * (r ** 2 + 2 * y * y)
        u = newx * fx + cx
        v = newy * fy + cy
        # clip 0
        u = np.where(u > 0, u, 0)
        v = np.where(v > 0, v, 0)
        # get distorted image size
        dest_h, dest_w = np.ceil(np.max(v)).astype(np.int32), np.ceil(np.max(u)).astype(np.int32)
        # pad with white
        dst_img = np.zeros((dest_h + 1, dest_w + 1, C)).astype(img.dtype) + 255
        u, v = np.rint(u).astype(np.int32), np.rint(v).astype(np.int32)
        dst_img[v, u] = img[Ys, Xs]
        return dst_img

    def apply_coords(self, coords):
        """
        coords should be a N * 2 array-like, containing N couples of (x, y) points
        """
        coords = np.asarray(coords, dtype=float).reshape(-1, 2)
        # points: N, 2
        cx, cy = self.param['cx'], self.param['cy']
        fx, fy = self.param['fx'], self.param['fy']
        k1, k2, k3, p1, p2 = self.param['k1'], self.param['k2'], self.param['k3'], self.param['p1'], self.param['p2']
        x = coords[:, 0]
        y = coords[:, 1]
        x = (x - cx) / fx
        y = (y - cy) / fy
        r = x*x + y*y

        newx = x * (1 + k1 * r + k2 * r * r + k3 * r * r * r) + 2*p1*x*y + p2*(r*r + 2*x*x)
        newy = y * (1 + k1 * r + k2 * r * r + k3 * r * r * r) + 2*p2*x*y + p1*(r*r + 2*y*y)
        u = newx * fx + cx
        v = newy * fy + cy
        # clip 0
        u = np.where(u > 0, u, 0)
        v = np.where(v > 0, v, 0)
        return np.stack((u, v), axis=1)

    def apply_segmentation(self, segmentation):
        segmentation = self.apply_image(segmentation)
        return segmentation


class RandomDistortion(T.Augmentation):
    def __init__(self, prob):
        super().__init__()
        self.prob = prob

    def generate_random_params(self, W, H, k_range=(-1.2, 1.2), p_range=(-0.1, 0.1)):  
        k1 = np.random.uniform(k_range[0], k_range[1])  
        k2 = np.random.uniform(k_range[0], k_range[1])  
        k3 = np.random.uniform(k_range[0], k_range[1])  
        p1 = np.random.uniform(p_range[0], p_range[1])  
        p2 = np.random.uniform(p_range[0], p_range[1])  

        return {  
            'fx': np.random.uniform(2000, 10000),  
            'fy': np.random.uniform(2000, 10000),  
            'cx': W / 2 - np.random.uniform(W * -0.2, W * 0.2),  
            'cy': H / 2 - np.random.uniform(H * -0.2, H * 0.2),  
            'k1': k1,  
            'k2': k2,  
            'k3': k3,  
            'p1': p1,  
            'p2': p2  
        }

    def get_transform(self, image):
        do = self._rand_range() < self.prob
        if not do:
            return T.NoOpTransform()
        H, W = image.shape[:2]
        param = self.generate_random_params(W, H)
        return DistortionTransform(param, (H, W))


class RotationTransform(T.RotationTransform):
    def apply_image(self, img, interp=None):
        """
        img should be a numpy array, formatted as Height * Width * Nchannels
        """
        if len(img) == 0 or self.angle % 360 == 0:
            return img
        assert img.shape[:2] == (self.h, self.w)
        interp = interp if interp is not None else self.interp
        return cv2.warpAffine(img, self.rm_image, (self.bound_w, self.bound_h), flags=interp, borderMode=cv2.BORDER_REPLICATE )


def resize(im, annos):
    min_size = (800, 800)
    max_size = 1600
    sample_style = "choice"
    aug = T.ResizeShortestEdge(min_size, max_size, sample_style)
    transform = aug.get_transform(im)
    im = transform.apply_image(im)
    for anno in annos:
        segms = anno['segmentation']
        new_segms = []
        for segm in segms:
            polygon = np.asarray(segm).reshape(-1, 2)
            polygon = transform.apply_polygons([polygon])[0]
            segm = polygon.reshape(-1).tolist()
            new_segms.append(segm)
        anno["segmentation"] = new_segms
    return im, annos


def random_rotation(im, annos):
    random_rotate_prob = 0.5
    rotate_angle_range = (-45, 45)
    if random.random() < random_rotate_prob:
        h, w, _ = im.shape
        angle = np.random.uniform(rotate_angle_range[0], rotate_angle_range[1])
        transform = RotationTransform(h, w, angle)
        im = transform.apply_image(im)
        for anno in annos:
            segms = anno['segmentation']
            new_segms = []
            for segm in segms:
                polygon = np.asarray(segm).reshape(-1, 2)
                polygon = transform.apply_polygons([polygon])[0]
                segm = polygon.reshape(-1).tolist()
                new_segms.append(segm)
            anno["segmentation"] = new_segms
    return im, annos


def random_distortion(im, annos):
    random_distortion_prob = 0.5
    aug = RandomDistortion(random_distortion_prob)
    transform = aug.get_transform(im)
    im = transform.apply_image(im)
    for anno in annos:
        segms = anno['segmentation']
        new_segms = []
        for segm in segms:
            polygon = np.asarray(segm).reshape(-1, 2)
            polygon = transform.apply_polygons([polygon])[0]
            segm = polygon.reshape(-1).tolist()
            new_segms.append(segm)
        anno["segmentation"] = new_segms
    return im, annos


def random_image_augmentation(im, annos):
    annos = interpolater_segmentation(annos)
    im, annos = random_rotation(im, annos)
    im, annos = random_distortion(im, annos)
    im, annos = resize(im, annos)
    for anno in annos:
        pts = []
        for segm in anno['segmentation']:
            pts.extend(segm)
        pts = np.asarray(pts).reshape(-1, 2)
        xmin, ymin = np.min(pts, axis=0)
        xmax, ymax = np.max(pts, axis=0)
        anno['bbox'] = [xmin, ymin, xmax - xmin, ymax - ymin]
    return im, annos


def aug_func(input_image_path, annos, output_image_path):
    im = cv2.imread(input_image_path)
    im, annos = random_image_augmentation(im, annos)
    cv2.imwrite(output_image_path, im)
    return annos

def create_augmented_dataset(mode, image_root, output_image_root):
    coco_api = COCO(f"{mode}.json")
    image_ids = list(coco_api.imgs.keys())
    os.makedirs(output_image_root, exist_ok=True)
    input_image_paths = [os.path.join(image_root, coco_api.imgs[image_id]['file_name']) for image_id in image_ids]
    output_image_paths = [os.path.join(output_image_root, coco_api.imgs[image_id]['file_name']) for image_id in image_ids]
    annos = [coco_api.imgToAnns[image_id] for image_id in image_ids]
    annos = p_map(aug_func, input_image_paths, annos, output_image_paths)
    coco_api.dataset['annotations'] = [anno for annos_per_image in annos for anno in annos_per_image]

    with open(f"{mode}_aug.json", "w") as fp:
        json.dump(coco_api.dataset, fp)


if __name__ == "__main__":
    # create_augmented_dataset("val", "val", "val_aug")
    # create_augmented_dataset("test", "test", "test_aug")
    create_augmented_dataset("examples", "examples", "examples_aug")
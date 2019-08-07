from __future__ import division
import argparse
import scipy.misc
import numpy as np
from joblib import Parallel, delayed
from tqdm import tqdm
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("dataset_dir", metavar='DIR',
                    help='path to original dataset')
parser.add_argument("--dataset-format", type=str, required=True,
                    choices=["kitti_raw", "kitti_odom", "cityscapes"])
parser.add_argument("--static-frames", default=None,
                    help="list of imgs to discard for being static, if not set will discard them based on speed \
                    (careful, on KITTI some frames have incorrect speed)")
parser.add_argument("--dump-root", type=str, required=True, help="Where to dump the data")
parser.add_argument("--height", type=int, default=128, help="image height")
parser.add_argument("--width", type=int, default=416, help="image width")
parser.add_argument("--num-threads", type=int, default=4, help="number of threads to use")

args = parser.parse_args()


def dump_example(scene):
    scene_list = data_loader.collect_scenes(scene)
    for scene_data in scene_list:
        dump_dir = args.dump_root/scene_data['rel_path']
        dump_dir.mkdir(parents=True, exist_ok=True)
        intrinsics = scene_data['intrinsics']
        fx = intrinsics[0, 0]
        fy = intrinsics[1, 1]
        cx = intrinsics[0, 2]
        cy = intrinsics[1, 2]

        dump_cam_file = dump_dir/'cam.txt'
        with open(dump_cam_file, 'w') as f:
            f.write('%f,0.,%f,0.,%f,%f,0.,0.,1.' % (fx, cx, fy, cy))

        for img, frame_nb in data_loader.get_scene_imgs(scene_data):
            dump_img_file = dump_dir/'{}.jpg'.format(frame_nb)
            scipy.misc.imsave(dump_img_file, img)

        if len([im_ for im_ in dump_dir.glob('*.jpg')]) < 3:
            shutil.rmtree(dump_dir)


def main():
    args.dump_root = Path(args.dump_root)
    args.dump_root.mkdir(parents=True, exist_ok=True)

    global data_loader

    if args.dataset_format == 'kitti_raw':
        from kitti_raw_loader import KittiRawLoader
        data_loader = KittiRawLoader(args.dataset_dir,
                                     static_frames_file=args.static_frames,
                                     img_height=args.height,
                                     img_width=args.width)

    elif args.dataset_format == "kitti_odom":
        from kitti_odometry_loader import KittiOdometryLoader
        data_loader = KittiOdometryLoader(args.dataset_dir,
                                          static_frames_file=args.static_frames,
                                          img_height=args.height,
                                          img_width=args.width,
                                          seq_length=5,
                                          train_list="./data/odometry_train.txt",
                                          val_list="./data/odometry_val.txt")

    elif args.dataset_format == 'cityscapes':
        raise("Not Implemented Error")
    else:
        raise("Please use assigned argument by dataset_format")

    print('Retrieving frames')
    Parallel(n_jobs=args.num_threads)(delayed(dump_example)(scene) for scene in tqdm(data_loader.scenes))
    # Split into train/val
    print('Generating train val lists')
    np.random.seed(8964)
    subfolders = args.dump_root.glob('*')
    with open(args.dump_root / 'train.txt', 'w') as tf:
        with open(args.dump_root / 'val.txt', 'w') as vf:
            for s in tqdm(subfolders):
                if s.is_dir():
                    if np.random.random() < 0.1 and args.dataset_format != "kitti_odom":
                        vf.write('{}\n'.format(s.name))
                    else:
                        tf.write('{}\n'.format(s.name))


if __name__ == '__main__':
    main()

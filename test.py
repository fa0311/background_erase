import glob
import pathlib

import cv2
import matplotlib.pyplot as plt
from rembg import new_session, remove
from tqdm import tqdm

from main import MODEL_NAME_LIST

MODEL_LOOP_LIST = [None] + MODEL_NAME_LIST

if __name__ == "__main__":
    images = glob.glob("input/*.JPG")

    fig, axs = plt.subplots(len(images), len(MODEL_LOOP_LIST), figsize=(20, 20))
    for i, model_name in tqdm(enumerate(MODEL_LOOP_LIST), total=len(MODEL_LOOP_LIST)):
        session = new_session(model_name or "u2net", ["CUDAExecutionProvider"])
        for j, image in tqdm(enumerate(images), total=len(images)):
            with open(image, "rb") as f:
                input_image = cv2.imread(image)
                input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
                if model_name:
                    output = remove(input_image, session=session)
                else:
                    output = input_image
                path = pathlib.Path(image)
                axs[j, i].imshow(output)
                axs[j, i].axis("off")
                axs[j, i].set_title(f"{model_name} {path.name}")
        del session

    fig.suptitle("Result")
    fig.tight_layout()
    fig.savefig("result.png")

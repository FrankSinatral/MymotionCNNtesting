import argparse
import os

import numpy as np
import torch
from matplotlib import pyplot as plt
from matplotlib.pyplot import figure
from torch.utils.data import DataLoader

from train import WaymoLoader, pytorch_neg_multi_log_likelihood_batch


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--save", type=str, required=True)
    parser.add_argument("--n-samples", type=int, required=False, default=50)

    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    if not os.path.exists(args.save):
        os.mkdir(args.save)

    model = torch.jit.load(args.model).cuda().eval()
    loader = DataLoader(
        WaymoLoader(args.data, return_vector=True),
        batch_size=1,
        num_workers=1,
        shuffle=False,
    )

    iii = 0
    with torch.no_grad():
        for x, y, is_available, vector_data in loader:
            x, y, is_available = map(lambda x: x.cuda(), (x, y, is_available))

            confidences_logits, logits = model(x)

            argmax = confidences_logits.argmax()
            confidences_logits = confidences_logits[:, argmax].unsqueeze(1)
            logits = logits[:, argmax].unsqueeze(1)

            loss = pytorch_neg_multi_log_likelihood_batch(
                y, logits, confidences_logits, is_available
            )
            confidences = torch.softmax(confidences_logits, dim=1)
            V = vector_data[0]

            X, idx = V[:, :44], V[:, 44].flatten()

            figure(figsize=(15, 15), dpi=80)
            for i in np.unique(idx):
                _X = X[idx == i]
                if _X[:, 5:12].sum() > 0:
                    plt.plot(_X[:, 0], _X[:, 1], linewidth=4, color="purple")
                else:
                    plt.plot(_X[:, 0], _X[:, 1], color="black")
            logits = logits.cpu().numpy()[0]
            y = y.cpu().numpy()[0]
            is_available = is_available.long().cpu().numpy()[0]
            plt.plot(
                y[is_available > 0][::10, 0],
                y[is_available > 0][::10, 1],
                "-o",
                label="GT",
            )
            plt.plot(
                logits[confidences[0].argmax()][is_available > 0][::10, 0],
                logits[confidences[0].argmax()][is_available > 0][::10, 1],
                "-o",
                label="PRED",
            )

            plt.title(loss.item())
            plt.legend()
            plt.savefig(
                os.path.join(args.save, f"{iii:0>2}_{loss.item():.3f}.png")
            )
            plt.close()
            iii += 1
            if iii == args.n_samples:
                break


if __name__ == "__main__":
    main()
"""Trenuje LeNet-5 na MNIST i zapisuje to, czego potrzebuje slajd „Algorytmiczny i trenowany”:

- img/lenet-warstwa-1.png … -5.png: wagi każdej warstwy w jej naturalnym kształcie, piksel = liczba
  (filtry splotowe jako kafelki 5×5, warstwy połączeń jako macierze wyjścia × wejścia;
  pomarańcz = dodatnia, szarość = ujemna, skala osobno dla każdej warstwy; bez biasów),
- img/mnist-cyfry.png: kilka cyfr ze zbioru uczącego,
- narzedzia/lenet.json: liczba parametrów, trafność na zbiorze testowym, wymiary obrazów.

Wyniki są commitowane; generuj_figury.py czyta je bez PyTorcha.
Środowisko: conda py312 (torch, torchvision, PIL). MNIST pobiera się do narzedzia/_mnist/ (nieśledzone);
tam też trafia wytrenowana sieć (lenet.pt) — gdy już jest, skrypt nie trenuje drugi raz.

Użycie:
    python narzedzia/trenuj_lenet.py
"""

import json
import math
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import datasets, transforms

KATALOG = Path(__file__).resolve().parent.parent
DANE = KATALOG / "narzedzia" / "_mnist"
EPOKI = 5
CYFRY = 8
POMARANCZ, SZARY = np.array([184, 100, 26]), np.array([70, 70, 70])


def lenet5():
    """LeNet-5 (LeCun i in. 1998) w dzisiejszym zapisie: ReLU i max-pooling zamiast tanh i podpróbkowania."""
    return nn.Sequential(
        nn.Conv2d(1, 6, 5, padding=2), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(6, 16, 5), nn.ReLU(), nn.MaxPool2d(2),
        nn.Flatten(),
        nn.Linear(400, 120), nn.ReLU(),
        nn.Linear(120, 84), nn.ReLU(),
        nn.Linear(84, 10),
    )


def trenuj(uczacy, testowy):
    torch.manual_seed(2026)
    siec = lenet5()
    opt = torch.optim.Adam(siec.parameters(), lr=1e-3)
    blad = nn.CrossEntropyLoss()
    for epoka in range(EPOKI):
        siec.train()
        for x, y in torch.utils.data.DataLoader(uczacy, batch_size=64, shuffle=True):
            opt.zero_grad()
            blad(siec(x), y).backward()
            opt.step()   # w ← w − η·∂L/∂w (w wersji Adama)
        trafnosc = sprawdz(siec, testowy)
        print(f"epoka {epoka + 1}: trafność na zbiorze testowym {trafnosc:.2%}")
    return siec


@torch.no_grad()
def sprawdz(siec, testowy):
    siec.eval()
    dobre = 0
    for x, y in torch.utils.data.DataLoader(testowy, batch_size=1000):
        dobre += (siec(x).argmax(1) == y).sum().item()
    return dobre / len(testowy)


def koloruj(w):
    skala = np.percentile(np.abs(w), 99) or 1.0
    t = np.clip(w / skala, -1, 1)[..., None]
    return np.where(t >= 0, 255 + t * (POMARANCZ - 255), 255 - t * (SZARY - 255))


def kafelki(w):
    """Filtry splotowe (wyjście, wejście, 5, 5) jako siatka kafelków z odstępem 1 piksela:
    kolumna = filtr (kanał wyjściowy), wiersz = kanał wejściowy."""
    wyj, wej, k, _ = w.shape
    kolory = koloruj(w)
    plotno = np.full((wej * (k + 1) - 1, wyj * (k + 1) - 1, 3), 255.0)
    for o in range(wyj):
        for i in range(wej):
            plotno[i * (k + 1):i * (k + 1) + k, o * (k + 1):o * (k + 1) + k] = kolory[o, i]
    return plotno


def obrazy_warstw(siec):
    wagi = [m.weight.detach().numpy() for m in siec if isinstance(m, (nn.Conv2d, nn.Linear))]
    obrazy = [kafelki(w) for w in wagi[:2]] + [koloruj(w) for w in wagi[2:]]
    wymiary = []
    for i, obraz in enumerate(obrazy, 1):
        Image.fromarray(obraz.round().astype(np.uint8)).save(
            KATALOG / "img" / f"lenet-warstwa-{i}.png", optimize=True)
        wymiary.append([obraz.shape[1], obraz.shape[0]])
    return wymiary, [list(w.shape) for w in wagi]


def obraz_cyfr(uczacy):
    pasek = np.concatenate([255 - uczacy.data[i].numpy() for i in range(CYFRY)], axis=1)
    Image.fromarray(pasek.astype(np.uint8)).save(KATALOG / "img" / "mnist-cyfry.png", optimize=True)
    return [int(uczacy.targets[i]) for i in range(CYFRY)]


if __name__ == "__main__":
    torch.set_num_threads(8)
    przeksztalc = transforms.ToTensor()
    uczacy = datasets.MNIST(DANE, train=True, download=True, transform=przeksztalc)
    testowy = datasets.MNIST(DANE, train=False, download=True, transform=przeksztalc)
    zapis = DANE / "lenet.pt"
    if zapis.exists():
        siec = lenet5()
        siec.load_state_dict(torch.load(zapis))
    else:
        siec = trenuj(uczacy, testowy)
        torch.save(siec.state_dict(), zapis)
    trafnosc = sprawdz(siec, testowy)
    n = sum(p.numel() for p in siec.parameters())
    wymiary, ksztalty = obrazy_warstw(siec)
    etykiety = obraz_cyfr(uczacy)
    opis = {
        "parametry": n,
        "trafnosc_testowa": round(trafnosc, 4),
        "epoki": EPOKI,
        "obrazy_uczace": len(uczacy),
        "obrazy_testowe": len(testowy),
        "warstwy_png": wymiary,
        "warstwy_ksztalt": ksztalty,
        "cyfry": etykiety,
    }
    (KATALOG / "narzedzia" / "lenet.json").write_text(json.dumps(opis, indent=2) + "\n", encoding="utf-8")
    print(f"LeNet-5: {n} parametrów, trafność {trafnosc:.2%}; obrazy warstw {wymiary}; cyfry {etykiety}")

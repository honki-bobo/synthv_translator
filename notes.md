### Composition and weighting of alternative phoneme sequences

```python
phoneme_seq = ["l", "j", "r"]
phoneme_map = {
  "l": [
    {"lang": "spanish", "ph": "l", "weight": 2.0},
    {"lang": "english", "ph": "l" }
  ],
  "j": [
    {"lang": "english", "ph": "y"},
    {"lang": "spanish", "ph": "y"},
    {"lang": "japanese", "ph": "y"}
  ],
  "r": [
    {"lang": "spanish", "ph": "r"},
    {"lang": "spanish", "ph": "rr"},
    {"lang": "english", "ph": "r"},
    {"lang": "japanese", "ph": "r"}
  ]
}

max_weight_all = max([len(ph) for _, ph in phoneme_map.items()])
phoneme_weight = (max_weight - idx) + (ph[idx]["weight"] if "weight" in ph[idx] else 0.0)
# shall return
[
    {
        "weight": 14.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "english", "ph": "y"},
            {"lang": "spanish",  "ph": "r"}
        ]
    },
    {
        "weight": 13.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "english", "ph": "y"},
            {"lang": "spanish", "ph": "rr"}
        ]
    },
    {
        "weight": 12.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "english", "ph": "y"},
            {"lang": "english", "ph": "r"}
        ]
    },
    {
        "weight": 11.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "english", "ph": "y"},
            {"lang": "japanese", "ph": "r"}
        ]
    },

    {
        "weight": 13.0,
        "single_lang": True,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "spanish",  "ph": "r"}
        ]
    },
    {
        "weight": 12.0,
        "single_lang": True,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "spanish", "ph": "rr"}
        ]
    },
    {
        "weight": 11.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "english", "ph": "r"}
        ]
    },
    {
        "weight": 10.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "japanese", "ph": "r"}
        ]
    },

    {
        "weight": 12.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "japanese", "ph": "y"},
            {"lang": "spanish",  "ph": "r"}
        ]
    },
    {
        "weight": 11.0,
        "single_lang": True,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "spanish", "ph": "rr"}
        ]
    },
    {
        "weight": 10.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "english", "ph": "r"}
        ]
    },
    {
        "weight": 9.0,
        "single_lang": False,
        "mapping": [
            {"lang": "spanish", "ph": "l", "weight": 2.0},
            {"lang": "spanish", "ph": "y"},
            {"lang": "japanese", "ph": "r"}
        ]
    },


    {
        "weight": 9.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "english", "ph": "y"},
            {"lang": "spanish",  "ph": "r"}
        ]
    },
    {
        "weight": 8.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "english", "ph": "y"},
            {"lang": "spanish", "ph": "rr"}
        ]
    },
    {
        "weight": 7.0,
        "single_lang": True,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "english", "ph": "y"},
            {"lang": "english", "ph": "r"}
        ]
    },
    {
        "weight": 6.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "english", "ph": "y"},
            {"lang": "japanese", "ph": "r"}
        ]
    },

    {
        "weight": 10.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "spanish",  "ph": "r"}
        ]
    },
    {
        "weight": 9.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "spanish", "ph": "rr"}
        ]
    },
    {
        "weight": 8.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "english", "ph": "r"}
        ]
    },
    {
        "weight": 7.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "japanese", "ph": "r"}
        ]
    },

    {
        "weight": 9.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "japanese", "ph": "y"},
            {"lang": "spanish",  "ph": "r"}
        ]
    },
    {
        "weight": 8.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "spanish", "ph": "rr"}
        ]
    },
    {
        "weight": 7.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "english", "ph": "r"}
        ]
    },
    {
        "weight": 6.0,
        "single_lang": False,
        "mapping": [
            {"lang": "english", "ph": "l"},
            {"lang": "spanish", "ph": "y"},
            {"lang": "japanese", "ph": "r"}
        ]
    }
]
def map_phoneme_sequences(phoneme_seq, phoneme_map):
    pass

```
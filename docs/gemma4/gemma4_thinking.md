# Thinking mode in Gemma

|---|---|---|---|---|
| [![](https://ai.google.dev/static/site-assets/images/docs/notebook-site-button.png)View on ai.google.dev](https://ai.google.dev/gemma/docs/capabilities/thinking) | [![](https://www.tensorflow.org/images/colab_logo_32px.png)Run in Google Colab](https://colab.research.google.com/github/google-gemma/cookbook/blob/main/docs/capabilities/thinking.ipynb) | [![](https://www.kaggle.com/static/images/logos/kaggle-logo-transparent-300.png)Run in Kaggle](https://kaggle.com/kernels/welcome?src=https://github.com/google-gemma/cookbook/blob/main/docs/capabilities/thinking.ipynb) | [![](https://ai.google.dev/images/cloud-icon.svg)Open in Vertex AI](https://console.cloud.google.com/vertex-ai/colab/import/https%3A%2F%2Fraw.githubusercontent.com%2Fgoogle-gemma%2Fcookbook%2Fmain%2Fdocs%2Fcapabilities%2Fthinking.ipynb) | [![](https://www.tensorflow.org/images/GitHub-Mark-32px.png)View source on GitHub](https://github.com/google-gemma/cookbook/blob/main/docs/capabilities/thinking.ipynb) |

Gemma is a family of lightweight, state-of-the-art open models built from the same research and technology used to create the [Gemini](https://deepmind.google/technologies/gemini/#introduction) models. Gemma 4 is designed to be the world's most efficient open-weight model family.

This document demonstrates how to use the thinking capabilities of Gemma 4 to generate reasoning processes before providing a final answer. You will learn how to enable thinking mode for both text-only and multimodal (image-text) tasks using the Hugging Face `transformers` library, and how to parse the output to separate thinking from the answer.

This notebook will run on T4 GPU.

## Install Python packages

Install the Hugging Face libraries required for running the Gemma model and making requests.

    # Install PyTorch & other libraries
    pip install torch accelerate

    # Install the transformers library
    pip install transformers

## Load Model

Use the `transformers` libraries to create an instance of a `processor` and `model` using the `AutoProcessor` and `AutoModelForImageTextToText` classes as shown in the following code example:

    MODEL_ID = "google/gemma-4-E2B-it" # @param ["google/gemma-4-E2B-it","google/gemma-4-E4B-it", "google/gemma-4-31B-it", "google/gemma-4-26B-A4B-it"]

    from transformers import AutoProcessor, AutoModelForMultimodalLM

    model = AutoModelForMultimodalLM.from_pretrained(MODEL_ID, dtype="auto", device_map="auto")
    processor = AutoProcessor.from_pretrained(MODEL_ID)

```
Loading weights:   0%|          | 0/2011 [00:00<?, ?it/s]
```

## A single text inference with Thinking

To generate a response using the model's thinking capabilities, pass `enable_thinking=True`, the processor will insert the correct thinking tokens into the prompt, instructing the model to think before responding.
>
> > [!NOTE]
> > **Note:** We've added an empty thinking token to the chat template for `gemma-4-26B-A4B-it` and `gemma-4-31B-it`. This stabilizes model output by suppressing "ghost" thought channels that may appear even when thinking is deactivated.
>
| Model Size | Thinking State | Template Structure / Output |
|---|---|---|
| **E2B/E4B** | **OFF** | `<|turn>user\n[Prompt]<turn|>\n<|turn>model` |
| **E2B/E4B** | **ON** | `<|turn>system\n<|think|><turn|>\n<|turn>user\n[Prompt]<turn|>\n<|turn>model` |
| **26B/31B** | **OFF** | ⚠️ `<|turn>user\n[Prompt]<turn|>\n<|turn>model\n<|channel>thought\n<channel|>` |
| **26B/31B** | **ON** | `<|turn>system\n<|think|><turn|>\n<|turn>user\n[Prompt]<turn|>\n<|turn>model` |

    from transformers import TextStreamer

    message = [
        {
            "role": "user", "content": "What is the water formula?"
        }
    ]

    text = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True, enable_thinking=True)
    inputs = processor(text=text, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[-1]

    streamer = TextStreamer(processor)
    outputs = model.generate(**inputs, streamer=streamer, max_new_tokens=1024)

```
<bos><|turn>system
<|think|><turn|>
<|turn>user
What is the water formula?<turn|>
<|turn>model
<|channel>thought
Thinking Process:

1.  **Analyze the Request:** The user is asking, "What is the water formula?"
2.  **Interpret the Ambiguity:** The term "water formula" is highly ambiguous. It could refer to several things:
    *   **Chemical Formula:** \\(\text{H}_2\text{O}\\) (the molecular formula).
    *   **Physical/Scientific Formula:** The properties of water (e.g., polarity, hydrogen bonding, specific heat).
    *   **Biological/Chemical Formula:** The role of water in biochemistry (e.g., solvation, hydration shells).
    *   **Mathematical Formula:** Equations relating to water cycles, thermodynamics, or fluid dynamics.
    *   **Culinary/Recipe Formula:** A specific recipe.
    *   **A specific context missing:** Is this related to chemistry, physics, biology, engineering, or something else?
3.  **Determine the Most Likely Interpretation:** In a general knowledge context, when someone asks for a "formula" related to water, they most often mean the fundamental chemical structure.
4.  **Formulate the Primary Answer (Chemical):** State the chemical formula and briefly explain what it represents.
5.  **Address the Ambiguity (Provide Context/Alternatives):** Since the request is vague, offer other possible interpretations so the user can clarify.
6.  **Review Constraints (Self-Correction/Identity Check):** I am Gemma 4, an LLM. I can provide factual information based on my knowledge base. No tools are needed. The answer should be clear and comprehensive.

7.  **Draft the Response Structure:**
    *   Start with the most direct answer (Chemical Formula).
    *   Explain the components and bonding.
    *   Offer context for other possible meanings. (Drafting the final response based on this structure.)<channel|>The term "water formula" can be interpreted in several ways, depending on the context (chemistry, physics, biology, etc.).

Here are the most common interpretations:

### 1. Chemical Formula (The Most Common Answer)

The fundamental chemical formula for water is:


$$\text{H}_2\text{O}$$


*   **H** represents the element **Hydrogen**.
*   **O** represents the element **Oxygen**.

This formula indicates that one molecule of water is composed of two hydrogen atoms covalently bonded to one oxygen atom.

### 2. Molecular Structure and Bonding

Beyond the formula, the "formula" also describes how the atoms interact:

*   **Polarity:** Water is a highly **polar** molecule. Oxygen is much more electronegative than hydrogen, meaning it pulls the shared electrons closer to itself. This creates a partial negative charge (\\(\delta^-\\)) on the oxygen atom and partial positive charges (\\(\delta^+\\)) on the hydrogen atoms.
*   **Hydrogen Bonding:** The polarity allows water molecules to form **hydrogen bonds** with each other. This strong attraction is responsible for water's unique physical properties, such as its high specific heat, its ability to dissolve many substances (its role as a universal solvent), and its high surface tension.

### 3. Formula in Physics/Thermodynamics

If you are referring to a physical formula, it might relate to:

*   **Specific Heat Capacity:** The amount of energy required to raise the temperature of a given mass of water by one degree.
*   **Density and Volume:** Equations relating the mass, volume, and density of water under different temperatures and pressures.

***

**In summary, if you are asking for the basic chemical makeup, the formula is \\(\text{H}_2\text{O}\\).**

If you are looking for a specific formula in a different field (like a mathematical equation or a biological reaction), please provide more context!<turn|>
```

Once the text is generated, the response will contain both the reasoning blocks and the final answer bounded by special tokens. You can use the `parse_response` utility to easily extract them into a dictionary containing `thinking` and `answer`.

    response = processor.decode(outputs[0][input_len:], skip_special_tokens=False)
    result = processor.parse_response(response)

    for key, value in result.items():
      if key == "role":
        print(f"Role: {value}")
      elif key == "thinking":
        print(f"\n=== Thoughts ===\n{value}")
      elif key == "content":
        print(f"\n=== Answer ===\n{value}")
      elif key == "tool_calls":
        print(f"\n=== Tool Calls ===\n{value}")
      else:
        print(f"\n{key}: {value}...\n")

```
Role: assistant

=== Thoughts ===
Thinking Process:

1.  **Analyze the Request:** The user is asking, "What is the water formula?"
2.  **Interpret the Ambiguity:** The term "water formula" is highly ambiguous. It could refer to several things:
    *   **Chemical Formula:** \\(\text{H}_2\text{O}\\) (the molecular formula).
    *   **Physical/Scientific Formula:** The properties of water (e.g., polarity, hydrogen bonding, specific heat).
    *   **Biological/Chemical Formula:** The role of water in biochemistry (e.g., solvation, hydration shells).
    *   **Mathematical Formula:** Equations relating to water cycles, thermodynamics, or fluid dynamics.
    *   **Culinary/Recipe Formula:** A specific recipe.
    *   **A specific context missing:** Is this related to chemistry, physics, biology, engineering, or something else?
3.  **Determine the Most Likely Interpretation:** In a general knowledge context, when someone asks for a "formula" related to water, they most often mean the fundamental chemical structure.
4.  **Formulate the Primary Answer (Chemical):** State the chemical formula and briefly explain what it represents.
5.  **Address the Ambiguity (Provide Context/Alternatives):** Since the request is vague, offer other possible interpretations so the user can clarify.
6.  **Review Constraints (Self-Correction/Identity Check):** I am Gemma 4, an LLM. I can provide factual information based on my knowledge base. No tools are needed. The answer should be clear and comprehensive.

7.  **Draft the Response Structure:**
    *   Start with the most direct answer (Chemical Formula).
    *   Explain the components and bonding.
    *   Offer context for other possible meanings. (Drafting the final response based on this structure.)

=== Answer ===
The term "water formula" can be interpreted in several ways, depending on the context (chemistry, physics, biology, etc.).

Here are the most common interpretations:

### 1. Chemical Formula (The Most Common Answer)

The fundamental chemical formula for water is:


$$\text{H}_2\text{O}$$


*   **H** represents the element **Hydrogen**.
*   **O** represents the element **Oxygen**.

This formula indicates that one molecule of water is composed of two hydrogen atoms covalently bonded to one oxygen atom.

### 2. Molecular Structure and Bonding

Beyond the formula, the "formula" also describes how the atoms interact:

*   **Polarity:** Water is a highly **polar** molecule. Oxygen is much more electronegative than hydrogen, meaning it pulls the shared electrons closer to itself. This creates a partial negative charge (\\(\delta^-\\)) on the oxygen atom and partial positive charges (\\(\delta^+\\)) on the hydrogen atoms.
*   **Hydrogen Bonding:** The polarity allows water molecules to form **hydrogen bonds** with each other. This strong attraction is responsible for water's unique physical properties, such as its high specific heat, its ability to dissolve many substances (its role as a universal solvent), and its high surface tension.

### 3. Formula in Physics/Thermodynamics

If you are referring to a physical formula, it might relate to:

*   **Specific Heat Capacity:** The amount of energy required to raise the temperature of a given mass of water by one degree.
*   **Density and Volume:** Equations relating the mass, volume, and density of water under different temperatures and pressures.

***

**In summary, if you are asking for the basic chemical makeup, the formula is \\(\text{H}_2\text{O}\\).**

If you are looking for a specific formula in a different field (like a mathematical equation or a biological reaction), please provide more context!
```

## A single image inference

The procedure for using the thinking model with visual data is very similar. You can provide an image as part of the `messages` array. Just ensure you pass the image to the processor along with the formatted text, and the model will reason about the visual input before responding.

    from PIL import Image
    import matplotlib.pyplot as plt

    prompt = "What is shown in this image?"
    image_url = "https://raw.githubusercontent.com/google-gemma/cookbook/refs/heads/main/Demos/sample-data/GoldenGate.png"

    # download image
    !wget -q {image_url} -O image.png
    image = Image.open("image.png")

    # Display all images
    print("=== Downloaded image ===")
    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
    ax.imshow(image)
    ax.set_title("Image 1")
    ax.axis("off")
    plt.tight_layout()
    plt.show()

    message = [
        {
            "role": "user", "content": [
              {"type": "image"},
              {"type": "text", "text": prompt}
            ]
        }
    ]

    text = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True, enable_thinking=True)
    inputs = processor(text=text, images=image, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[-1]

    outputs = model.generate(**inputs, max_new_tokens=1024)
    response = processor.decode(outputs[0][input_len:], skip_special_tokens=False)

    result = processor.parse_response(response)

    for key, value in result.items():
      if key == "role":
        print(f"Role: {value}")
      elif key == "thinking":
        print(f"\n=== Thoughts ===\n{value}")
      elif key == "content":
        print(f"\n=== Answer ===\n{value}")
      elif key == "tool_calls":
        print(f"\n=== Tool Calls ===\n{value}")
      else:
        print(f"\n{key}: {value}...\n")

```
=== Downloaded image ===
```

![png](https://ai.google.dev/static/gemma/docs/capabilities/thinking_files/output_WZg8nr-FEwOe_1.png)

```
Role: assistant

=== Thoughts ===
Here's a thinking process to arrive at the suggested description:

1.  **Analyze the Image Content:**
    *   **Dominant Feature:** A large suspension bridge with distinctive red/orange trusswork. This is immediately recognizable as the Golden Gate Bridge.
    *   **Setting:** Water (a large body of water, likely the bay/ocean).
    *   **Foreground/Midground:**
        *   Water in the immediate foreground (dark blue/green).
        *   A rocky outcrop/island in the middle foreground.
        *   A substantial stone/brick structure to the left (part of the bridge approach or a related structure).
    *   **Background:** Hazy landmasses/hills behind the bridge.
    *   **Sky:** Clear, light blue sky.
    *   **Atmosphere/Lighting:** Bright daylight, clear weather.

2.  **Identify Key Elements for Description:**
    *   The Bridge (Golden Gate Bridge).
    *   The Water/Bay.
    *   The Coastal/Land features.

3.  **Draft the Description (Focusing on detail and clarity):**
    *   *Initial thought:* It's a picture of the Golden Gate Bridge over the water.
    *   *Refinement (Adding detail):* The image shows the iconic red suspension bridge spanning a body of water. There is a rocky island in the foreground and some structures on the shore.
    *   *Enhancement (Adding context and visual appeal):* Mention the color, the scale, and the atmosphere.

4.  **Final Polish and Structure (Grouping similar ideas):** (This leads to the final structured response.)

    *   *Identification:* State clearly what the main subject is.
    *   *Setting:* Describe the environment (water, sky).
    *   *Details:* Mention specific foreground and background elements.

5.  **Review against the original prompt:** (The prompt asks "What is shown in this image?") The description accurately reflects the visual evidence. (Self-Correction: Ensure the identification is confident, which it is, based on the structure and color.)

=== Answer ===
This image shows the **Golden Gate Bridge** spanning a body of water, likely the San Francisco Bay.

Here is a breakdown of what is visible:

* **The Golden Gate Bridge:** The iconic red/orange suspension bridge dominates the frame, stretching across the water. Its distinctive structure and massive towers are clearly visible.
* **Water:** A large expanse of blue-green water fills the foreground and midground.
* **Foreground Elements:** In the immediate foreground, there is a dark, rocky outcrop or small island.
* **Shoreline/Structures:** To the left, there are stone and brick structures, suggesting the land or approach to the bridge.
* **Background:** Hazy hills or landmasses are visible in the distance behind the bridge.
* **Atmosphere:** The scene is brightly lit under a clear, light blue sky, suggesting fair weather.

In summary, it is a scenic photograph capturing the majestic view of the Golden Gate Bridge.
```

## Summary and next steps

In this guide, you learned how to use the thinking capabilities of Gemma 4 models to generate reasoning processes before final answers. You covered:

- Enabling thinking mode using `enable_thinking=True` in `apply_chat_template`.
- Using `TextStreamer` to observe the thinking process in real-time.
- Parsing the combined output into separate `thinking` and `answer` blocks using `parse_response`.
- Applying thinking capabilities to multimodal tasks (image + text).

### Next Steps

Explore more capabilities of Gemma 4:

- [Prompt and system instructions](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4)
- [Function calling](https://ai.google.dev/gemma/docs/capabilities/function-calling-gemma4)
- [Run Gemma overview](https://ai.google.dev/gemma/docs/run)
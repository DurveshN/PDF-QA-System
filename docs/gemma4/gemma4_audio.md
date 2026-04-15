# Audio understanding

|---|---|---|---|---|
| [![](https://ai.google.dev/static/site-assets/images/docs/notebook-site-button.png)View on ai.google.dev](https://ai.google.dev/gemma/docs/capabilities/audio) | [![](https://www.tensorflow.org/images/colab_logo_32px.png)Run in Google Colab](https://colab.research.google.com/github/google-gemma/cookbook/blob/main/docs/capabilities/audio.ipynb) | [![](https://www.kaggle.com/static/images/logos/kaggle-logo-transparent-300.png)Run in Kaggle](https://kaggle.com/kernels/welcome?src=https://github.com/google-gemma/cookbook/blob/main/docs/capabilities/audio.ipynb) | [![](https://ai.google.dev/images/cloud-icon.svg)Open in Vertex AI](https://console.cloud.google.com/vertex-ai/colab/import/https%3A%2F%2Fraw.githubusercontent.com%2Fgoogle-gemma%2Fcookbook%2Fmain%2Fdocs%2Fcapabilities%2Faudio.ipynb) | [![](https://www.tensorflow.org/images/GitHub-Mark-32px.png)View source on GitHub](https://github.com/google-gemma/cookbook/blob/main/docs/capabilities/audio.ipynb) |

Starting with [Gemma 3n](https://ai.google.dev/gemma/docs/gemma-3n), you can use audio directly into your prompts and workflows. Audio and spoken language are rich sources of data for capturing user intents, recording information about the world around us, and understanding
specific problems to be solved.

This guide provides an overview of the audio processing capabilities of [Gemma 4](https://ai.google.dev/gemma/docs/core), including automatic speech recognition (ASR), translation, and general speech understanding.

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

## Audio data

Digital audio data can come in many formats and levels of resolution. The actual audio formats you can use with Gemma, such as MP3 and WAV formats, are determined by the framework you choose to convert sound data into tensors. Here are some specific considerations for preparing audio data for processing with Gemma:

- **Token cost:** Each second of audio is 25 tokens for Gemma 4. (6.25 tokens for Gemma 3n).
- **Clip length:** Audio supports a maximum length of 30 seconds.
- **Audio channels:** Audio data is processed as a single audio channel. If you are using multi-channel audio, such as left and right channels, consider reducing the data to a single channel by removing channels or combining the sound data into a single channel.
- **Technical Encoding:**
  - **Sample Rate:** 16kHz using 32ms frames.
  - **Bit Depth:** 32-bit float format, with samples normalized within the range of \[-1, 1\].

If the audio data you plan to process is significantly different from the input
processing, particularly in terms of channels, sample rate and bit depth,
consider resampling or trimming your audio data to match the data
resolution handled by the model.

## Audio encoding

While high-level libraries (such as Hugging Face `AutoProcessor`) often handle audio preprocessing automatically, you may sometimes need to implement custom encoding.

When encoding audio data with your own code implementation for use with Gemma, you should follow the recommended conversion process. If you are working
with audio files encoded in a specific format, such as MP3 or WAV encoded data,
you must first decode these to samples using a library such as `ffmpeg`. Once
the data is decoded, convert the audio into mono-channel, 16 kHz float32
waveforms in the range \[-1, 1\]. For example, if you are working with stereo
signed 16-bit PCM integer WAV files at 44.1 kHz, follow these steps:

- Resample the audio data to 16 kHz
- Downmix from stereo to mono by averaging the 2 channels
- Convert from int16 to float32, and divide by 32768.0 to scale to the range \[-1, 1\]

> > [!NOTE]
> > **Note:** When resampling audio to 16 kHz, you should use a Fourier method for best results, such as `scipy.signal.resample` or `librosa.sample(res_type ='scipy')`.
>
## Speech to text

Gemma 4 E2B and E4B are trained for multilingual speech recognition, allowing you to transcribe audio input in various languages into text. The following code examples show how to prompt the model to transcribe text from audio files using Hugging Face Transformers:

    RESOURCE_URL_PREFIX = "https://raw.githubusercontent.com/google-gemma/cookbook/refs/heads/main/Demos/sample-data/"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Transcribe the following speech segment in its original language. Follow these specific instructions for formatting the answer:\n* Only output the transcription, with no newlines.\n* When transcribing numbers, write the digits, i.e. write 1.7 and not one point seven, and write 3 instead of three."},
                #{"type": "text", "text": "Transcribe the following speech segment in English into English text. Follow these specific instructions for formatting the answer:\n* Only output the transcription, with no newlines.\n* When transcribing numbers, write the digits, i.e. write 1.7 and not one point seven, and write 3 instead of three."},
                {"type": "audio", "audio": f"{RESOURCE_URL_PREFIX}journal1.wav"},
            ]
        }
    ]

    input_ids = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True, return_dict=True,
            return_tensors="pt",
    )
    input_ids = input_ids.to(model.device, dtype=model.dtype)

    outputs = model.generate(**input_ids, max_new_tokens=64)

    text = processor.batch_decode(
        outputs,
        skip_special_tokens=False,
        clean_up_tokenization_spaces=False
    )
    print(text[0])

```
<bos><|turn>user
Transcribe the following speech segment in its original language. Follow these specific instructions for formatting the answer:

* Only output the transcription, with no newlines.
* When transcribing numbers, write the digits, i.e. write 1.7 and not one point seven, and write 3 instead of three.<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|><turn|>
<|turn>model
I woke up early today feeling really fresh the morning light was beautiful and I enjoyed a nice cup of coffee<turn|>
```

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Give me a concise overview of these audio files."},
                {"type": "text", "text": "journal1:"},
                {"type": "audio", "audio": f"{RESOURCE_URL_PREFIX}journal1.wav"},
                {"type": "text", "text": "journal2:"},
                {"type": "audio", "audio": f"{RESOURCE_URL_PREFIX}journal2.wav"},
                {"type": "text", "text": "journal3:"},
                {"type": "audio", "audio": f"{RESOURCE_URL_PREFIX}journal3.wav"},
                {"type": "text", "text": "journal4:"},
                {"type": "audio", "audio": f"{RESOURCE_URL_PREFIX}journal4.wav"},
                {"type": "text", "text": "journal5:"},
                {"type": "audio", "audio": f"{RESOURCE_URL_PREFIX}journal5.wav"},
            ]
        }
    ]

    input_ids = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True, return_dict=True,
            return_tensors="pt",
    )
    input_ids = input_ids.to(model.device, dtype=model.dtype)

    outputs = model.generate(**input_ids, max_new_tokens=1024)

    text = processor.batch_decode(
        outputs,
        skip_special_tokens=False,
        clean_up_tokenization_spaces=False
    )
    print(text[0])

```
<bos><|turn>user
Give me a concise overview of these audio files.journal1:<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|>journal2:<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|>journal3:<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|>journal4:<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|>journal5:<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|><turn|>
<|turn>model
Here is a concise overview of the audio files:

**Journal 1:** The speaker felt refreshed, enjoyed a morning ride, a cup of coffee, and was generally happy.

**Journal 2:** The speaker spent the afternoon at the park, which was a perfect day for a walk, and enjoyed watching the cherry blossoms.

**Journal 3:** The speaker finished the day with a good book, feeling grateful for simple moments and ready for more.

**Journal 4:** The speaker returned from work, admiring the sunset, and enjoyed a clear view from the train.

**Journal 5:** The speaker had a great lunch with an old friend, enjoyed catching up, and felt happy about the day.<turn|>
```

## Automated speech translation

Gemma 4 E2B and E4B are trained for multilingual speech translation tasks, allowing you to translate spoken audio directly into another language. The following code examples show how to prompt the model to translate spoken audio into text using Hugging Face Transformers:

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Transcribe the following speech segment in English, then translate it into Korean. When formatting the answer, first output the transcription in English, then one newline, then output the string 'Korean: ', then the translation in Korean."},
                {"type": "audio", "audio": "https://ai.google.dev/gemma/docs/audio/roses-are.wav"},
            ]
        }
    ]

    input_ids = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True, return_dict=True,
            return_tensors="pt",
    )
    input_ids = input_ids.to(model.device, dtype=model.dtype)

    outputs = model.generate(**input_ids, max_new_tokens=64)

    text = processor.batch_decode(
        outputs,
        skip_special_tokens=False,
        clean_up_tokenization_spaces=False
    )
    print(text[0])

```
<bos><|turn>user
Transcribe the following speech segment in English, then translate it into Korean. When formatting the answer, first output the transcription in English, then one newline, then output the string 'Korean: ', then the translation in Korean.<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|><turn|>
<|turn>model
Roses are red, violets are blue.
Korean: 장미는 빨갛고, 제비꽃은 파랗다.<turn|>
```

## Automatic Speech Translation / Automatic Speech Recognition

Try this by yourself

    pip install ipywebrtc

```
Collecting ipywebrtc
  Downloading ipywebrtc-0.6.0-py2.py3-none-any.whl.metadata (825 bytes)
Downloading ipywebrtc-0.6.0-py2.py3-none-any.whl (260 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 260.7/260.7 kB 22.6 MB/s eta 0:00:00
Installing collected packages: ipywebrtc
Successfully installed ipywebrtc-0.6.0
```

Press the circle button and start speaking. Click the circle button again when you are finished. The widget will immediately begin to play back what it captured.

    from google.colab import output
    output.enable_custom_widget_manager()

    from ipywebrtc import AudioRecorder, CameraStream

    camera = CameraStream(constraints={'audio': True,'video':False})
    recorder = AudioRecorder(stream=camera)
    recorder

```
AudioRecorder(audio=Audio(value=b'', format='webm'), stream=CameraStream(constraints={'audio': True, 'video': …
```

Convert webm file to wav format that PyTorch can understand.

    with open('/content/recording.webm', 'wb') as f:
        f.write(recorder.audio.value)
    !ffmpeg -i /content/recording.webm /content/recording.wav -y

```
ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021 the FFmpeg developers
  built with gcc 11 (Ubuntu 11.2.0-19ubuntu1)
  configuration: --prefix=/usr --extra-version=0ubuntu0.22.04.1 --toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu --arch=amd64 --enable-gpl --disable-stripping --enable-gnutls --enable-ladspa --enable-libaom --enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca --enable-libcdio --enable-libcodec2 --enable-libdav1d --enable-libflite --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libgme --enable-libgsm --enable-libjack --enable-libmp3lame --enable-libmysofa --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-libpulse --enable-librabbitmq --enable-librubberband --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libssh --enable-libtheora --enable-libtwolame --enable-libvidstab --enable-libvorbis --enable-libvpx --enable-libwebp --enable-libx265 --enable-libxml2 --enable-libxvid --enable-libzimg --enable-libzmq --enable-libzvbi --enable-lv2 --enable-omx --enable-openal --enable-opencl --enable-opengl --enable-sdl2 --enable-pocketsphinx --enable-librsvg --enable-libmfx --enable-libdc1394 --enable-libdrm --enable-libiec61883 --enable-chromaprint --enable-frei0r --enable-libx264 --enable-shared
  libavutil      56. 70.100 / 56. 70.100
  libavcodec     58.134.100 / 58.134.100
  libavformat    58. 76.100 / 58. 76.100
  libavdevice    58. 13.100 / 58. 13.100
  libavfilter     7.110.100 /  7.110.100
  libswscale      5.  9.100 /  5.  9.100
  libswresample   3.  9.100 /  3.  9.100
  libpostproc    55.  9.100 / 55.  9.100
Input #0, matroska,webm, from '/content/recording.webm':
  Metadata:
    encoder         : Chrome
  Duration: 00:00:04.02, start: 0.000000, bitrate: 131 kb/s
  Stream #0:0(eng): Audio: opus, 48000 Hz, mono, fltp (default)
Stream mapping:
  Stream #0:0 -> #0:0 (opus (native) -> pcm_s16le (native))
Press [q] to stop, [?] for help
Output #0, wav, to '/content/recording.wav':
  Metadata:
    ISFT            : Lavf58.76.100
  Stream #0:0(eng): Audio: pcm_s16le ([1][0][0][0] / 0x0001), 48000 Hz, mono, s16, 768 kb/s (default)
    Metadata:
      encoder         : Lavc58.134.100 pcm_s16le
size=     383kB time=00:00:04.01 bitrate= 779.7kbits/s speed=60.6x    
video:0kB audio:382kB subtitle:0kB other streams:0kB global headers:0kB muxing overhead: 0.019914%
```

### ASR

    messages = [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Transcribe the following speech segment in its original language. Follow these specific instructions for formatting the answer:\n* Only output the transcription, with no newlines.\n* When transcribing numbers, write the digits, i.e. write 1.7 and not one point seven, and write 3 instead of three."},
        {"type": "audio", "audio": "/content/recording.wav"},
      ]
    }]

    input_ids = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True, return_dict=True,
            return_tensors="pt",
    )
    input_ids = input_ids.to(model.device, dtype=model.dtype)

    outputs = model.generate(**input_ids, max_new_tokens=64)

    text = processor.batch_decode(
        outputs,
        skip_special_tokens=False,
        clean_up_tokenization_spaces=False
    )
    print(text[0])

```
<bos><|turn>user
Transcribe the following speech segment in its original language. Follow these specific instructions for formatting the answer:

* Only output the transcription, with no newlines.
* When transcribing numbers, write the digits, i.e. write 1.7 and not one point seven, and write 3 instead of three.<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|><turn|>
<|turn>model
How can I get to the station?<turn|>
```

### AST

    messages = [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Transcribe the following speech segment in English, then translate it into Korean. When formatting the answer, first output the transcription in English, then one newline, then output the string 'Korean: ', then the translation in Korean."},
        {"type": "audio", "audio": "/content/recording.wav"},
      ]
    }]

    input_ids = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True, return_dict=True,
            return_tensors="pt",
    )
    input_ids = input_ids.to(model.device, dtype=model.dtype)

    outputs = model.generate(**input_ids, max_new_tokens=64)

    text = processor.batch_decode(
        outputs,
        skip_special_tokens=False,
        clean_up_tokenization_spaces=False
    )
    print(text[0])

```
<bos><|turn>user
Transcribe the following speech segment in English, then translate it into Korean. When formatting the answer, first output the transcription in English, then one newline, then output the string 'Korean: ', then the translation in Korean.<|audio><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><|audio|><audio|><turn|>
<|turn>model
How can I get to the station?
Korean: 역에 어떻게 가나요?<turn|>
```

## Summary and next steps

In this guide, you learned how to process audio using Gemma 4 models. The examples demonstrated how to perform Speech-to-Text (ASR) to transcribe spoken language, as well as Automated Speech Translation (AST) to translate spoken audio directly into another language. You also saw how to capture audio from a microphone in a notebook environment for processing.

Check out the following documentation for further reading.

- [Run Gemma overview](https://ai.google.dev/gemma/docs/core/gemma/docs/run)
- [Prompt with visual data](https://ai.google.dev/gemma/docs/core/gemma/docs/capabilities/vision/prompt-with-visual-data)
- [Thinking mode](https://ai.google.dev/gemma/docs/core/gemma/docs/capabilities/thinking)
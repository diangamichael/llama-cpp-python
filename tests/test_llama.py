import llama_cpp

MODEL = "./vendor/llama.cpp/models/ggml-vocab.bin"


def test_llama():
    llama = llama_cpp.Llama(model_path=MODEL, vocab_only=True)

    assert llama
    assert llama.ctx is not None

    text = b"Hello World"

    assert llama.detokenize(llama.tokenize(text)) == text


def test_llama_patch(monkeypatch):
    llama = llama_cpp.Llama(model_path=MODEL, vocab_only=True)

    ## Set up mock function
    def mock_eval(*args, **kwargs):
        return 0

    monkeypatch.setattr("llama_cpp.llama_cpp.llama_eval", mock_eval)

    output_text = " jumps over the lazy dog."
    output_tokens = llama.tokenize(output_text.encode("utf-8"))
    token_eos = llama.token_eos()
    n = 0

    def mock_sample(*args, **kwargs):
        nonlocal n
        if n < len(output_tokens):
            n += 1
            return output_tokens[n - 1]
        else:
            return token_eos

    monkeypatch.setattr("llama_cpp.llama_cpp.llama_sample_top_p_top_k", mock_sample)

    text = "The quick brown fox"

    ## Test basic completion until eos
    n = 0  # reset
    completion = llama.create_completion(text, max_tokens=20)
    assert completion["choices"][0]["text"] == output_text
    assert completion["choices"][0]["finish_reason"] == "stop"

    ## Test streaming completion until eos
    n = 0  # reset
    chunks = llama.create_completion(text, max_tokens=20, stream=True)
    assert "".join(chunk["choices"][0]["text"] for chunk in chunks) == output_text
    assert completion["choices"][0]["finish_reason"] == "stop"

    ## Test basic completion until stop sequence
    n = 0  # reset
    completion = llama.create_completion(text, max_tokens=20, stop=["lazy"])
    assert completion["choices"][0]["text"] == " jumps over the "
    assert completion["choices"][0]["finish_reason"] == "stop"

    ## Test streaming completion until stop sequence
    n = 0  # reset
    chunks = llama.create_completion(text, max_tokens=20, stream=True, stop=["lazy"])
    assert (
        "".join(chunk["choices"][0]["text"] for chunk in chunks) == " jumps over the "
    )
    assert completion["choices"][0]["finish_reason"] == "stop"

    ## Test basic completion until length
    n = 0  # reset
    completion = llama.create_completion(text, max_tokens=2)
    assert completion["choices"][0]["text"] == " j"
    assert completion["choices"][0]["finish_reason"] == "length"

    ## Test streaming completion until length
    n = 0  # reset
    chunks = llama.create_completion(text, max_tokens=2, stream=True)
    assert "".join(chunk["choices"][0]["text"] for chunk in chunks) == " j"
    assert completion["choices"][0]["finish_reason"] == "length"


def test_llama_pickle():
    import pickle
    import tempfile
    fp = tempfile.TemporaryFile()
    llama = llama_cpp.Llama(model_path=MODEL, vocab_only=True)
    pickle.dump(llama, fp)
    fp.seek(0)
    llama = pickle.load(fp)

    assert llama
    assert llama.ctx is not None

    text = b"Hello World"

    assert llama.detokenize(llama.tokenize(text)) == text
    
    
def test_model_output(llama):
    for prompt in PROMPTS:
        completion = llama.create_completion(prompt, max_tokens=20)
        assert "choices" in completion
        assert "text" in completion["choices"][0]
        assert isinstance(completion["choices"][0]["text"], str)

def test_temperature(llama):
    for prompt in PROMPTS:
        for temperature in TEMPERATURES:
            completion = llama.create_completion(prompt, max_tokens=20, temperature=temperature)
            assert "choices" in completion
            assert "text" in completion["choices"][0]
            assert isinstance(completion["choices"][0]["text"], str)

def test_top_k(llama):
    for prompt in PROMPTS:
        for top_k in TOP_K_VALUES:
            completion = llama.create_completion(prompt, max_tokens=20, top_k=top_k)
            assert "choices" in completion
            assert "text" in completion["choices"][0]
            assert isinstance(completion["choices"][0]["text"], str)


def test_repetition_penalty(llama):
    for prompt in PROMPTS:
        for repetition_penalty in REPETITION_PENALTIES:
            completion = llama.create_completion(prompt, max_tokens=20, repetition_penalty=repetition_penalty)
            assert "choices" in completion
            assert "text" in completion["choices"][0]
            assert isinstance(completion["choices"][0]["text"], str)

def test_long_prompt(llama):
    prompt = "a" * (llama.get_max_sequence_length() + 1)
    completion = llama.create_completion(prompt, max_tokens=20)
    assert "choices" in completion
    assert "text" in completion["choices"][0]
    assert isinstance(completion["choices"][0]["text"], str)

def test_out_of_vocab(llama):
    prompt = "the quick brown fux"
    completion = llama.create_completion(prompt, max_tokens=20)
    assert "choices" in completion
    assert "text" in completion["choices"][0]
    assert isinstance(completion["choices"][0]["text"], str)
    assert "out of vocabulary" in completion["warning"]

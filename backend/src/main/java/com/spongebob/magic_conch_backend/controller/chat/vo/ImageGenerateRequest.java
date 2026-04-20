package com.spongebob.magic_conch_backend.controller.chat.vo;

public class ImageGenerateRequest {

    private String prompt;

    private String imagePath;

    public String getPrompt() {
        return prompt;
    }

    public void setPrompt(String prompt) {
        this.prompt = prompt;
    }

    public String getImagePath() {
        return imagePath;
    }

    public void setImagePath(String imagePath) {
        this.imagePath = imagePath;
    }
}

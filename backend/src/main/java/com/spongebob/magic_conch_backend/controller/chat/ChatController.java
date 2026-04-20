package com.spongebob.magic_conch_backend.controller.chat;

import com.spongebob.magic_conch_backend.common.enums.ResultCode;
import com.spongebob.magic_conch_backend.common.vo.Result;
import com.spongebob.magic_conch_backend.controller.chat.vo.ImageGenerateRequest;
import com.spongebob.magic_conch_backend.service.ChatService;
import io.micrometer.common.util.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/chat")
public class ChatController {

    @Autowired
    private ChatService chatService;

    @RequestMapping("/generate")
    public Result generate(@RequestParam String prompt) {
        if (StringUtils.isBlank(prompt)) {
            return Result.error(ResultCode.PARAM_INVALID, "prompt不能为空");
        }

        try {
            return Result.success(chatService.callAiForOneReply(prompt));
        } catch (Exception e) {
            return Result.error(ResultCode.ERROR, "文本问答调用失败：" + e.getMessage());
        }
    }

    @PostMapping("/image-generate")
    public Result imageGenerate(@RequestBody ImageGenerateRequest request) {
        if (request == null || StringUtils.isBlank(request.getPrompt())) {
            return Result.error(ResultCode.PARAM_INVALID, "prompt不能为空");
        }
        if (StringUtils.isBlank(request.getImagePath())) {
            return Result.error(ResultCode.PARAM_INVALID, "imagePath不能为空");
        }

        try {
            return Result.success(chatService.callAiForImageReply(request.getPrompt(), request.getImagePath()));
        } catch (Exception e) {
            return Result.error(ResultCode.ERROR, "图像问答调用失败：" + e.getMessage());
        }
    }
}

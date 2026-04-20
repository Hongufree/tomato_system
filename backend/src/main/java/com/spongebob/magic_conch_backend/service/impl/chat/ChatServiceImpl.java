package com.spongebob.magic_conch_backend.service.impl.chat;

import com.fasterxml.jackson.databind.JsonNode;
import com.spongebob.magic_conch_backend.config.AiServiceConfig;
import com.spongebob.magic_conch_backend.service.ChatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

@Service
public class ChatServiceImpl implements ChatService {

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private AiServiceConfig aiServiceConfig;

    @Override
    public String callAiForOneReply(String prompt) {
        return callDeepSeek(prompt);
    }

    @Override
    public String callAiForImageReply(String prompt, String imagePath) {
        throw new UnsupportedOperationException(
                "The current DeepSeek cloud integration does not support image QA from a local file path. Please describe the image in text and ask again."
        );
    }

    private String callDeepSeek(String prompt) {
        String url = aiServiceConfig.getBaseUrl() + aiServiceConfig.getChatPath();

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(aiServiceConfig.getApiKey());

        Map<String, Object> requestBody = Map.of(
                "model", aiServiceConfig.getModel(),
                "messages", List.of(
                        Map.of("role", "system", "content", aiServiceConfig.getSystemPrompt()),
                        Map.of("role", "user", "content", prompt)
                ),
                "stream", false
        );

        HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);
        JsonNode response = restTemplate.postForObject(url, requestEntity, JsonNode.class);
        JsonNode contentNode = response == null
                ? null
                : response.path("choices").path(0).path("message").path("content");

        if (contentNode == null || contentNode.isMissingNode() || contentNode.isNull()) {
            throw new IllegalStateException("DeepSeek returned an empty response");
        }

        return contentNode.asText();
    }
}

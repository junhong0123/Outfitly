using System.Net.Http.Json;
using System.Text.Json;
using Outfitly.Models;

namespace Outfitly.Services
{
    public class AiEngineClient
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<AiEngineClient> _logger;

        public AiEngineClient(HttpClient httpClient, ILogger<AiEngineClient> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
        }

        public async Task<AiRecommendationResponse?> GetRecommendationsAsync(
            string userId,
            int topK = 8,
            CancellationToken cancellationToken = default)
        {
            var path = $"recommend/{Uri.EscapeDataString(userId)}?top_k={topK}&storefront_only=true&rerank=true&rerank_pool_size=200&popularity_weight=0.10";

            try
            {
                return await _httpClient.GetFromJsonAsync<AiRecommendationResponse>(path, cancellationToken);
            }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or NotSupportedException or JsonException)
            {
                _logger.LogWarning(ex, "Unable to load recommendations from the AI engine.");
                return null;
            }
        }

        public async Task<AiChatResponse> ChatAsync(
            string message,
            string? userId,
            int topK = 5,
            CancellationToken cancellationToken = default)
        {
            var payload = new AiEngineChatRequest
            {
                Message = message,
                UserId = userId,
                TopK = topK
            };

            try
            {
                using var response = await _httpClient.PostAsJsonAsync("chat", payload, cancellationToken);
                if (!response.IsSuccessStatusCode)
                {
                    _logger.LogWarning("AI chat request failed with status code {StatusCode}.", response.StatusCode);
                    return OfflineChatResponse();
                }

                var chatResponse = await response.Content.ReadFromJsonAsync<AiChatResponse>(cancellationToken);
                return chatResponse ?? OfflineChatResponse();
            }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or NotSupportedException or JsonException)
            {
                _logger.LogWarning(ex, "Unable to reach the AI chat service.");
                return OfflineChatResponse();
            }
        }

        private static AiChatResponse OfflineChatResponse()
        {
            return new AiChatResponse
            {
                IsFallback = true,
                Answer = "The AI assistant is temporarily unavailable. Please try again after the AI service is running.",
                Sources = new List<AiSource>()
            };
        }
    }
}

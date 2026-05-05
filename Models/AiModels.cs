using System.Text.Json.Serialization;

namespace Outfitly.Models
{
    public class AiRecommendationResponse
    {
        [JsonPropertyName("user_id")]
        public string UserId { get; set; } = string.Empty;

        [JsonPropertyName("cold_start")]
        public bool ColdStart { get; set; }

        [JsonPropertyName("recommendations")]
        public List<AiRecommendationItem> Recommendations { get; set; } = new();
    }

    public class AiRecommendationItem
    {
        [JsonPropertyName("product_id")]
        public int ProductId { get; set; }

        [JsonPropertyName("score")]
        public double Score { get; set; }
    }

    public class AiRecommendationsViewModel
    {
        public List<Product> Products { get; set; } = new();
        public bool IsAiPowered { get; set; }
        public bool ColdStart { get; set; }
        public string StatusMessage { get; set; } = string.Empty;
    }

    public class AiChatRequest
    {
        public string Message { get; set; } = string.Empty;
        public int TopK { get; set; } = 5;
    }

    public class AiChatResponse
    {
        [JsonPropertyName("answer")]
        public string Answer { get; set; } = string.Empty;

        [JsonPropertyName("sources")]
        public List<AiSource> Sources { get; set; } = new();

        [JsonPropertyName("is_fallback")]
        public bool IsFallback { get; set; }
    }

    public class AiSource
    {
        [JsonPropertyName("type")]
        public string Type { get; set; } = string.Empty;

        [JsonPropertyName("id")]
        public int? Id { get; set; }

        [JsonPropertyName("title")]
        public string Title { get; set; } = string.Empty;

        [JsonPropertyName("price")]
        public decimal? Price { get; set; }

        [JsonPropertyName("image_url")]
        public string? ImageUrl { get; set; }

        [JsonPropertyName("url")]
        public string? Url { get; set; }
    }

    public class AiEngineChatRequest
    {
        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;

        [JsonPropertyName("user_id")]
        public string? UserId { get; set; }

        [JsonPropertyName("top_k")]
        public int TopK { get; set; } = 5;
    }
}

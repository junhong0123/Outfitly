using Microsoft.AspNetCore.Identity;

namespace Outfitly.Models
{
    /// <summary>
    /// Tracks user interactions with products for AI recommendation engine.
    /// Critical for future AI/ML features.
    /// </summary>
    public class UserInteraction
    {
        public int Id { get; set; }
        public string? UserId { get; set; } // Nullable to support anonymous browsing
        public int ProductId { get; set; }
        public string InteractionType { get; set; } = string.Empty; // "View", "AddToCart", "Purchase"
        public DateTime TimeStamp { get; set; } = DateTime.UtcNow;

        // Navigation properties
        public IdentityUser? User { get; set; }
        public Product? Product { get; set; }
    }
}

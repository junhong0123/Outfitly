using Microsoft.AspNetCore.Identity;
using System.ComponentModel.DataAnnotations;

namespace Outfitly.Models
{
    /// <summary>
    /// Represents a saved shipping address for a user (max 3 per user)
    /// </summary>
    public class UserAddress
    {
        public int Id { get; set; }

        [Required]
        public string UserId { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string FirstName { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string LastName { get; set; } = string.Empty;

        [Required]
        [MaxLength(200)]
        public string AddressLine1 { get; set; } = string.Empty;

        [MaxLength(200)]
        public string? AddressLine2 { get; set; }

        [Required]
        [MaxLength(100)]
        public string City { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string StateProvince { get; set; } = string.Empty;

        [Required]
        [MaxLength(20)]
        public string ZipPostalCode { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string Country { get; set; } = string.Empty;

        [MaxLength(20)]
        public string? PhoneNumber { get; set; }

        public bool IsDefault { get; set; } = false;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        // Navigation property
        public IdentityUser? User { get; set; }
    }
}

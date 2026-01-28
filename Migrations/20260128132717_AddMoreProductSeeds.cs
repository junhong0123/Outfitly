using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace Outfitly.Migrations
{
    /// <inheritdoc />
    public partial class AddMoreProductSeeds : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.InsertData(
                table: "Products",
                columns: new[] { "Id", "AvailableColors", "AvailableSizes", "Category", "CreatedAt", "Description", "ImageUrl", "Name", "Price", "StockQuantity" },
                values: new object[,]
                {
                    { 6, "Blue,Gray,Beige", "S,M,L,XL", "Bottoms", new DateTime(2024, 1, 2, 0, 0, 0, 0, DateTimeKind.Unspecified), "Elegant linen pants perfect for business casual.", "https://placehold.co/600x400?text=Linen+Pants", "Tailored Linen Pants", 89.00m, 45 },
                    { 7, "Brown,Black,Tan", "One Size", "Accessories", new DateTime(2024, 1, 2, 0, 0, 0, 0, DateTimeKind.Unspecified), "Genuine leather crossbody bag with adjustable strap.", "https://placehold.co/600x400?text=Crossbody+Bag", "Leather Crossbody Bag", 129.00m, 20 },
                    { 8, "Gray,Navy,Camel", "S,M,L", "Outerwear", new DateTime(2024, 1, 3, 0, 0, 0, 0, DateTimeKind.Unspecified), "Timeless wool coat for the winter season.", "https://placehold.co/600x400?text=Wool+Coat", "Classic Wool Coat", 249.00m, 15 },
                    { 9, "White,Pink,Cream", "XS,S,M,L", "Tops", new DateTime(2024, 1, 3, 0, 0, 0, 0, DateTimeKind.Unspecified), "Luxurious silk blend blouse for formal occasions.", "https://placehold.co/600x400?text=Silk+Blouse", "Silk Blend Blouse", 79.00m, 35 },
                    { 10, "Blue,Black", "S,M,L,XL", "Outerwear", new DateTime(2024, 1, 4, 0, 0, 0, 0, DateTimeKind.Unspecified), "Classic denim jacket that never goes out of style.", "https://placehold.co/600x400?text=Denim+Jacket", "Denim Jacket", 119.00m, 40 },
                    { 11, "Black,Beige,Navy", "XS,S,M,L,XL", "Bottoms", new DateTime(2024, 1, 4, 0, 0, 0, 0, DateTimeKind.Unspecified), "Comfortable wide leg trousers with a modern silhouette.", "https://placehold.co/600x400?text=Wide+Leg+Trousers", "Wide Leg Trousers", 95.00m, 55 },
                    { 12, "Cream,Gray,Black,Burgundy", "S,M,L", "Tops", new DateTime(2024, 1, 5, 0, 0, 0, 0, DateTimeKind.Unspecified), "Ultra-soft 100% cashmere sweater for ultimate comfort.", "https://placehold.co/600x400?text=Cashmere+Sweater", "Cashmere Sweater", 159.00m, 20 },
                    { 13, "Black,Brown,Cognac", "36,37,38,39,40,41", "Footwear", new DateTime(2024, 1, 5, 0, 0, 0, 0, DateTimeKind.Unspecified), "Stylish ankle boots with comfortable block heel.", "https://placehold.co/600x400?text=Ankle+Boots", "Ankle Boots", 189.00m, 30 },
                    { 14, "Black,Gray,Beige", "S,M,L,XL", "Outerwear", new DateTime(2024, 1, 6, 0, 0, 0, 0, DateTimeKind.Unspecified), "Trendy oversized blazer for a chic look.", "https://placehold.co/600x400?text=Oversized+Blazer", "Oversized Blazer", 199.00m, 25 },
                    { 15, "Black,Navy,Olive", "XS,S,M,L", "Bottoms", new DateTime(2024, 1, 6, 0, 0, 0, 0, DateTimeKind.Unspecified), "Elegant pleated midi skirt for any occasion.", "https://placehold.co/600x400?text=Midi+Skirt", "Pleated Midi Skirt", 75.00m, 40 },
                    { 16, "Khaki,Black,Navy", "One Size", "Accessories", new DateTime(2024, 1, 7, 0, 0, 0, 0, DateTimeKind.Unspecified), "Durable canvas backpack with laptop compartment.", "https://placehold.co/600x400?text=Canvas+Backpack", "Canvas Backpack", 69.00m, 50 },
                    { 17, "Navy/White,Red/White,Green/White", "S,M,L,XL,XXL", "Tops", new DateTime(2024, 1, 7, 0, 0, 0, 0, DateTimeKind.Unspecified), "Classic striped polo shirt for casual weekends.", "https://placehold.co/600x400?text=Polo+Shirt", "Striped Polo Shirt", 45.00m, 60 },
                    { 18, "Black,Brown", "S,M,L,XL", "Accessories", new DateTime(2024, 1, 8, 0, 0, 0, 0, DateTimeKind.Unspecified), "Premium leather belt with silver buckle.", "https://placehold.co/600x400?text=Leather+Belt", "Leather Belt", 55.00m, 80 },
                    { 19, "Burgundy,Navy,Emerald", "XS,S,M,L", "Dresses", new DateTime(2024, 1, 8, 0, 0, 0, 0, DateTimeKind.Unspecified), "Flowing wrap maxi dress perfect for evening events.", "https://placehold.co/600x400?text=Maxi+Dress", "Wrap Maxi Dress", 129.00m, 20 },
                    { 20, "Black,Gray,Navy", "S,M,L,XL", "Bottoms", new DateTime(2024, 1, 9, 0, 0, 0, 0, DateTimeKind.Unspecified), "Comfortable athletic joggers for workouts or lounging.", "https://placehold.co/600x400?text=Athletic+Joggers", "Athletic Joggers", 65.00m, 70 }
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 6);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 7);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 8);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 9);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 10);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 11);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 12);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 13);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 14);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 15);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 16);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 17);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 18);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 19);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 20);
        }
    }
}

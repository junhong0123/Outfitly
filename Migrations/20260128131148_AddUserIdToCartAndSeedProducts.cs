using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace Outfitly.Migrations
{
    /// <inheritdoc />
    public partial class AddUserIdToCartAndSeedProducts : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "UserId",
                table: "CartItems",
                type: "nvarchar(max)",
                nullable: false,
                defaultValue: "");

            migrationBuilder.InsertData(
                table: "Products",
                columns: new[] { "Id", "AvailableColors", "AvailableSizes", "Category", "CreatedAt", "Description", "ImageUrl", "Name", "Price", "StockQuantity" },
                values: new object[,]
                {
                    { 1, "White,Black,Gray", "S,M,L,XL", "Tops", new DateTime(2024, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), "A premium quality cotton t-shirt for everyday wear.", "https://placehold.co/600x400?text=White+Tee", "Classic White Tee", 29.99m, 100 },
                    { 2, "Blue,Black", "30,32,34,36", "Bottoms", new DateTime(2024, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), "Comfortable slim fit jeans with a modern look.", "https://placehold.co/600x400?text=Jeans", "Slim Fit Jeans", 59.99m, 50 },
                    { 3, "Navy,Olive", "M,L,XL", "Outerwear", new DateTime(2024, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), "Perfect for chilly evenings, this jacket is both stylish and functional.", "https://placehold.co/600x400?text=Jacket", "Lightweight Bomber Jacket", 89.99m, 30 },
                    { 4, "Red,Blue,White", "8,9,10,11", "Footwear", new DateTime(2024, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), "High-performance running shoes with excellent cushioning.", "https://placehold.co/600x400?text=Sneakers", "Running Sneakers", 79.99m, 40 },
                    { 5, "Pink,Yellow", "XS,S,M", "Dresses", new DateTime(2024, 1, 1, 0, 0, 0, 0, DateTimeKind.Unspecified), "A breezy and beautiful dress for summer outings.", "https://placehold.co/600x400?text=Summer+Dress", "Summer Floral Dress", 49.99m, 25 }
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 1);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 2);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 3);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 4);

            migrationBuilder.DeleteData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 5);

            migrationBuilder.DropColumn(
                name: "UserId",
                table: "CartItems");
        }
    }
}

import pandas as pd
import pickle
import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import ollama


# ============================================================
# PRODUCT RECOMMENDATION MODULE
# Q6 + Q7 + WEB APPLICATION
# ============================================================

products = pd.read_csv("data/products.csv")

products["ProductName"] = products["ProductName"].fillna("")
products["Category"] = products["Category"].fillna("")
products["Brand"] = products["Brand"].fillna("")
products["Description"] = products["Description"].fillna("")


# ============================================================
# TF-IDF SEARCH TEXT
# ============================================================

products["SearchText"] = (
    products["ProductName"] + " "
    + products["Category"] + " "
    + products["Brand"] + " "
    + products["Description"]
)


# ============================================================
# LOAD / CREATE TF-IDF
# ============================================================

TFIDF_PATH = "models/tfidf_vectorizer.pkl"
VECTOR_PATH = "models/product_vectors.pkl"


def create_tfidf():

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )

    vectors = vectorizer.fit_transform(
        products["SearchText"]
    )

    os.makedirs("models", exist_ok=True)

    with open(TFIDF_PATH, "wb") as file:
        pickle.dump(vectorizer, file)

    with open(VECTOR_PATH, "wb") as file:
        pickle.dump(vectors, file)

    return vectorizer, vectors


if (
    os.path.exists(TFIDF_PATH)
    and os.path.exists(VECTOR_PATH)
):

    try:

        with open(TFIDF_PATH, "rb") as file:
            tfidf = pickle.load(file)

        with open(VECTOR_PATH, "rb") as file:
            product_vectors = pickle.load(file)

        if product_vectors.shape[0] != len(products):
            raise ValueError("Old TF-IDF vectors.")

    except Exception:

        print("Creating new TF-IDF model...")
        tfidf, product_vectors = create_tfidf()

else:

    print("Creating TF-IDF model...")
    tfidf, product_vectors = create_tfidf()


# ============================================================
# QUERY HELPERS
# ============================================================

def is_highest_rating_query(query):

    query = query.lower()

    phrases = [
        "highest rating",
        "highest rated",
        "best rated",
        "top rated",
        "best rating",
        "highest-rated"
    ]

    return any(
        phrase in query
        for phrase in phrases
    )


def is_cheapest_query(query):

    query = query.lower()

    phrases = [
        "cheap",
        "cheapest",
        "lowest price",
        "low price",
        "budget",
        "affordable",
        "inexpensive"
    ]

    return any(
        phrase in query
        for phrase in phrases
    )


def extract_brand(query):

    query = query.lower()

    brands = [
        str(brand).lower()
        for brand in products["Brand"].unique()
    ]

    for brand in brands:

        if brand in query:
            return brand

    return None


def extract_category(query):

    query = query.lower()

    categories = [
        str(category).lower()
        for category in products["Category"].unique()
    ]

    for category in categories:

        if category in query:
            return category

    return None


# ============================================================
# RECOMMEND PRODUCTS
# ============================================================

def recommend_products(user_query, top_n=3):

    query = user_query.lower()

    # ========================================================
    # SPECIAL CASE 1:
    # HIGHEST RATING
    # ========================================================

    if is_highest_rating_query(query):

        candidates = products.copy()

        # If user mentioned a category
        category = extract_category(query)

        if category:

            filtered = candidates[
                candidates["Category"]
                .str.lower()
                .eq(category)
            ]

            if not filtered.empty:
                candidates = filtered

        # If user mentioned a brand
        brand = extract_brand(query)

        if brand:

            filtered = candidates[
                candidates["Brand"]
                .str.lower()
                .eq(brand)
            ]

            if not filtered.empty:
                candidates = filtered

        # Sort by rating
        candidates = candidates.sort_values(
            by=["Rating", "Price"],
            ascending=[False, True]
        )

        selected = candidates.head(top_n)

        results = []

        for _, product in selected.iterrows():

            results.append({
                "ProductID": int(product["ProductID"]),
                "ProductName": product["ProductName"],
                "Category": product["Category"],
                "Brand": product["Brand"],
                "Price": float(product["Price"]),
                "Description": product["Description"],
                "Rating": float(product["Rating"]),
                "Similarity": 1.0
            })

        return results


    # ========================================================
    # SPECIAL CASE 2:
    # CHEAPEST / BUDGET
    # ========================================================

    if is_cheapest_query(query):

        candidates = products.copy()

        category = extract_category(query)

        if category:

            filtered = candidates[
                candidates["Category"]
                .str.lower()
                .eq(category)
            ]

            if not filtered.empty:
                candidates = filtered

        brand = extract_brand(query)

        if brand:

            filtered = candidates[
                candidates["Brand"]
                .str.lower()
                .eq(brand)
            ]

            if not filtered.empty:
                candidates = filtered

        # Sort by price first, rating second
        candidates = candidates.sort_values(
            by=["Price", "Rating"],
            ascending=[True, False]
        )

        selected = candidates.head(top_n)

        results = []

        for _, product in selected.iterrows():

            results.append({
                "ProductID": int(product["ProductID"]),
                "ProductName": product["ProductName"],
                "Category": product["Category"],
                "Brand": product["Brand"],
                "Price": float(product["Price"]),
                "Description": product["Description"],
                "Rating": float(product["Rating"]),
                "Similarity": 1.0
            })

        return results


    # ========================================================
    # NORMAL TF-IDF SEARCH
    # ========================================================

    query_vector = tfidf.transform(
        [user_query]
    )

    similarity_scores = cosine_similarity(
        query_vector,
        product_vectors
    )[0]

    final_scores = similarity_scores.copy()


    # ========================================================
    # BRAND BOOST
    # ========================================================

    brand = extract_brand(query)

    if brand:

        for index, product in products.iterrows():

            if (
                str(product["Brand"]).lower()
                == brand
            ):

                final_scores[index] += 0.40


    # ========================================================
    # CATEGORY BOOST
    # ========================================================

    category = extract_category(query)

    if category:

        for index, product in products.iterrows():

            if (
                str(product["Category"]).lower()
                == category
            ):

                final_scores[index] += 0.20


    # ========================================================
    # RATING BOOST
    # ========================================================

    ratings = products["Rating"].astype(float)

    rating_score = ratings / 5.0

    final_scores += (
        rating_score.values * 0.15
    )


    # ========================================================
    # TOP PRODUCTS
    # ========================================================

    top_indices = (
        final_scores
        .argsort()[-top_n:][::-1]
    )


    results = []

    for index in top_indices:

        product = products.iloc[index]

        results.append({
            "ProductID": int(product["ProductID"]),
            "ProductName": product["ProductName"],
            "Category": product["Category"],
            "Brand": product["Brand"],
            "Price": float(product["Price"]),
            "Description": product["Description"],
            "Rating": float(product["Rating"]),
            "Similarity": float(similarity_scores[index])
        })

    return results


# ============================================================
# OLLAMA RECOMMENDATION
# ============================================================

def generate_recommendation(
    user_query,
    products_list
):

    product_context = ""

    for product in products_list:

        product_context += f"""
Product Name: {product["ProductName"]}
Category: {product["Category"]}
Brand: {product["Brand"]}
Price: ₹{product["Price"]:.0f}
Rating: {product["Rating"]}
Description: {product["Description"]}
Similarity Score: {product["Similarity"]:.2f}

"""


    prompt = f"""
You are an e-commerce product recommendation assistant.

User question:
{user_query}

Retrieved products:
{product_context}

Choose the best product from the retrieved products.

Respond using exactly this format:

Product: <product name>
Brand: <brand>
Price: ₹<price>
Rating: <rating>
Reason: <short reason>

IMPORTANT:

- Use ONLY the information provided.
- Do not invent specifications.
- Do not claim a laptop is designed for gaming,
  office work, programming or students unless the
  product information explicitly says so.
- For a gaming/office/student request where the
  database does not contain that information,
  say that the recommendation is based on the
  available product information.
- Do not invent performance comparisons.
- Keep the response short.
"""


    response = ollama.chat(
        model="qwen2.5",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


# ============================================================
# WEB APPLICATION FUNCTION
# ============================================================

def handle_recommendation(user_query):

    retrieved_products = recommend_products(
        user_query,
        top_n=3
    )

    response = generate_recommendation(
        user_query,
        retrieved_products
    )

    return {
        "products": retrieved_products,
        "response": response
    }
# Gap.com API Documentation

This document contains information about the APIs used by Gap.com's web application, discovered through network traffic analysis.

## Overview

Gap.com uses various APIs to power its web application, including product catalog, search, user authentication, shopping cart, and more. This document catalogs these APIs and their structures.

## API Endpoints

### 1. Product Catalog API

**Base URL**: `TBD`

**Authentication**: `TBD`

#### Endpoints:

##### 1.1 Get Products

- **URL**: `TBD`
- **Method**: `GET`
- **Parameters**:
  - `TBD`
- **Response Structure**:
  ```json
  {
    "products": [
      {
        "id": "product_id",
        "name": "Product Name",
        "price": {
          "current": 0.00,
          "original": 0.00
        },
        "images": ["url1", "url2"],
        "colors": ["color1", "color2"],
        "sizes": ["size1", "size2"]
      }
    ],
    "pagination": {
      "total": 0,
      "page": 0,
      "pageSize": 0
    }
  }
  ```

##### 1.2 Get Product Details

- **URL**: `TBD`
- **Method**: `GET`
- **Parameters**:
  - `TBD`
- **Response Structure**:
  ```json
  {
    "product": {
      "id": "product_id",
      "name": "Product Name",
      "description": "Product description",
      "price": {
        "current": 0.00,
        "original": 0.00
      },
      "images": ["url1", "url2"],
      "colors": [
        {
          "name": "Color Name",
          "code": "color_code",
          "image": "color_image_url"
        }
      ],
      "sizes": [
        {
          "name": "Size Name",
          "code": "size_code",
          "inStock": true
        }
      ],
      "details": [
        {
          "title": "Detail Title",
          "content": "Detail Content"
        }
      ]
    }
  }
  ```

### 2. Search API

**Base URL**: `TBD`

**Authentication**: `TBD`

#### Endpoints:

##### 2.1 Search Products

- **URL**: `TBD`
- **Method**: `GET`
- **Parameters**:
  - `TBD`
- **Response Structure**:
  ```json
  {
    "results": [
      {
        "id": "product_id",
        "name": "Product Name",
        "price": {
          "current": 0.00,
          "original": 0.00
        },
        "thumbnail": "thumbnail_url"
      }
    ],
    "filters": [
      {
        "name": "Filter Name",
        "options": [
          {
            "name": "Option Name",
            "count": 0
          }
        ]
      }
    ],
    "pagination": {
      "total": 0,
      "page": 0,
      "pageSize": 0
    }
  }
  ```

### 3. User Authentication API

**Base URL**: `TBD`

**Authentication**: `TBD`

#### Endpoints:

##### 3.1 Login

- **URL**: `TBD`
- **Method**: `POST`
- **Parameters**:
  - `TBD`
- **Response Structure**:
  ```json
  {
    "token": "auth_token",
    "user": {
      "id": "user_id",
      "email": "user_email",
      "firstName": "First Name",
      "lastName": "Last Name"
    }
  }
  ```

### 4. Shopping Cart API

**Base URL**: `TBD`

**Authentication**: `TBD`

#### Endpoints:

##### 4.1 Get Cart

- **URL**: `TBD`
- **Method**: `GET`
- **Parameters**:
  - `TBD`
- **Response Structure**:
  ```json
  {
    "cart": {
      "id": "cart_id",
      "items": [
        {
          "id": "item_id",
          "productId": "product_id",
          "name": "Product Name",
          "price": 0.00,
          "quantity": 0,
          "color": "Color",
          "size": "Size",
          "image": "image_url"
        }
      ],
      "summary": {
        "subtotal": 0.00,
        "tax": 0.00,
        "shipping": 0.00,
        "total": 0.00,
        "discount": 0.00
      }
    }
  }
  ```

##### 4.2 Add to Cart

- **URL**: `TBD`
- **Method**: `POST`
- **Parameters**:
  - `TBD`
- **Response Structure**:
  ```json
  {
    "success": true,
    "cart": {
      "id": "cart_id",
      "itemCount": 0,
      "subtotal": 0.00
    }
  }
  ```

## Rate Limits

`TBD`

## Authentication Methods

`TBD`

## Common Headers

`TBD`

## Error Responses

`TBD`

## Notes

This documentation will be updated as more API endpoints are discovered through our analysis of Gap.com's network traffic. 
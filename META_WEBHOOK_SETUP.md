# Meta Lead Ads Webhook Setup Guide

This guide details the complete process for configuring and connecting Meta Lead Ads webhooks to the Southeast Landmark CRM. By connecting Facebook Lead Ads, new leads generated from your Facebook or Instagram campaigns will automatically push into the CRM system in real-time, instantly starting the SLA countdown timer for your sales executives.

## Step-by-Step Meta Lead Ads Webhook Setup

### Prerequisites
Before you begin, ensure you have the following ready:
- A Facebook Developer Account (register at developers.facebook.com if needed)
- A Facebook App (configured as a **Business** type app)
- A Facebook Page connected to the App where your ads will run
- Your CRM server must be publicly accessible and configured with a valid HTTPS certificate (Let's Encrypt or similar). Facebook requires all webhooks to use HTTPS.

### Step 1: Create Facebook App
1. Go to [Facebook Developers](https://developers.facebook.com)
2. Click on **'My Apps'** in the top right corner, then click **'Create App'**
3. Select **'Business'** as your app type and click Next.
4. Fill in the App Name: `'Southeast Landmark CRM'` (or your preferred name)
5. Enter the contact email and select your Business Manager account if applicable.
6. Once created, copy the **App ID** from the dashboard header and paste it into your `.env` file as `META_APP_ID`.

### Step 2: Add Lead Ads Product
1. In your new App dashboard, navigate to the **'Add Product'** section.
2. Scroll down until you find **'Lead Ads'** and click **'Set Up'**.
3. Follow the prompts to add your target Facebook Page to the setup configuration.

### Step 3: Get Page Access Token
To authenticate API calls between the CRM and Facebook, you need a Page Access Token.
1. Go to **Tools → Graph API Explorer** in the developer portal.
2. In the "Application" dropdown, select your newly created App.
3. Click "Generate Access Token" and select "Get User Token". When prompted for permissions, ensure you select: `pages_manage_ads`, `pages_read_engagement`, and `leads_retrieval`.
4. Once the User Token is generated, click the token dropdown again and select your specific Facebook Page to exchange it for a **Page Access Token**.
5. Copy this long-lived token and paste it into your `.env` file as `META_PAGE_ACCESS_TOKEN`.

### Step 4: Set Up Webhook
1. Back in your App dashboard, go to the **Webhooks** product section (add it from "Add Product" if not visible).
2. In the dropdown at the top, select to subscribe to the **'Page'** object.
3. Click "Subscribe to this object" and enter your Callback URL. This should be your public CRM domain followed by the webhook path: `https://yourdomain.com/webhooks/meta`
4. For the **Verify Token**, create a random, secure string (e.g., a UUID or a long randomized password). Paste this exact string into your `.env` file as `META_VERIFY_TOKEN`.
5. Click "Verify and Save". Facebook will ping your server to confirm the token matches.
6. After saving, find the **'leadgen'** field in the list of subscriptions and click "Subscribe".

### Step 5: Get App Secret
1. Navigate to **Settings → Basic** in the left sidebar.
2. Click "Show" next to the App Secret (you may need to enter your Facebook password).
3. Copy the App Secret and paste it into your `.env` file as `META_APP_SECRET`. This is used to validate incoming webhook HMAC signatures.

### Step 6: Subscribe Page to Webhook
You must tell Facebook to route your specific page's leads to this application. Run the following curl command from your terminal, replacing the placeholders with your actual values:
```bash
curl -X POST 'https://graph.facebook.com/v19.0/{PAGE_ID}/subscribed_apps' \
  -H 'Authorization: Bearer {PAGE_ACCESS_TOKEN}' \
  -d 'subscribed_fields=leadgen'
```

### Step 7: Test the Webhook
1. Go to the [Lead Ads Testing Tool](https://developers.facebook.com/tools/lead-ads-testing) in the developer portal.
2. Select your Page and Form, then click **'Create Lead'**.
3. Check your CRM dashboard immediately. The new test lead should appear.
4. Verify that the SLA timer for the lead has started correctly.

### Step 8: Lead Form Field Mapping
The Southeast Landmark CRM is configured to map these standard Facebook Lead Ad fields automatically:
- `full_name` → `Contact.full_name`
- `email` → `Contact.email`
- `phone_number` → `Contact.phone` (The CRM will normalize the phone number format)
- Any custom questions added to your lead form are securely stored in the CRM's `raw_payload` database column for reference.

### Troubleshooting:
- **Webhook verification fails:** Ensure the `META_VERIFY_TOKEN` in your `.env` exactly matches what you pasted into Facebook. Ensure your server is running and accessible via HTTPS.
- **HMAC validation fails:** Ensure the `META_APP_SECRET` is correct. The CRM uses this to cryptographically verify the payload is genuinely from Meta.
- **Leads not appearing:** Use the Graph API explorer to verify that your Page subscription is actively pointing to your App.

### Admin Dashboard:
After completing the setup, you can monitor webhook health, view incoming payload logs, and check subscription status directly from the CRM Admin portal at: `https://yourdomain.com/settings/meta-webhook`

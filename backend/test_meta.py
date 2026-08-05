from app import create_app
from app.extensions import db
from app.tasks import process_meta_webhook
from unittest.mock import patch

app = create_app()

def test():
    with app.app_context():
        # Mock payload as it would come from Facebook
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "PAGE_ID",
                    "time": 1234567890,
                    "changes": [
                        {
                            "value": {
                                "form_id": "123",
                                "leadgen_id": "TEST_LEAD_ID_999",
                                "created_time": 1234567890,
                                "page_id": "PAGE_ID"
                            },
                            "field": "leadgen"
                        }
                    ]
                }
            ]
        }

        # Mock the Facebook Graph API response so it doesn't fail trying to connect to Meta
        def mock_fetch_meta_lead(app, leadgen_id):
            return {
                "id": leadgen_id,
                "field_data": [
                    {"name": "full_name", "values": ["Test Auto Lead"]},
                    {"name": "email", "values": ["test.auto.lead@example.com"]},
                    {"name": "phone_number", "values": ["+8801700000000"]}
                ]
            }

        print("Simulating incoming Meta webhook...")
        with patch('app.tasks._fetch_meta_lead', side_effect=mock_fetch_meta_lead):
            process_meta_webhook(payload, app)
        
        print("Webhook processed. Checking database results...")
        
        from app.models import Contact, Opportunity
        contact = Contact.query.filter_by(email='test.auto.lead@example.com').first()
        if contact:
            print(f"✅ Contact created: {contact.full_name}")
            # Get the most recent opportunity for this contact
            opp = Opportunity.query.filter_by(contact_id=contact.id).order_by(Opportunity.id.desc()).first()
            if opp:
                if opp.assigned_to:
                    print(f"✅ Lead Assigned to: {opp.assigned_to.full_name} (Role: {opp.assigned_to.role.value})")
                else:
                    print(f"⏳ Lead left UNASSIGNED (Pending). No Lead Owner was scheduled at this exact time.")
            else:
                print("❌ No opportunity found for this contact.")
        else:
            print("❌ Contact was not created.")

if __name__ == "__main__":
    test()

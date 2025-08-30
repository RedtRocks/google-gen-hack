#!/usr/bin/env python3
"""
Local testing script for Legal Document Demystifier
"""

import requests
import json
import os
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8080"
TEST_DOCUMENT = """
RENTAL AGREEMENT

This Rental Agreement is entered into between John Smith (Landlord) and Jane Doe (Tenant).

TERMS:
1. Monthly rent: $1,500 due on the 1st of each month
2. Security deposit: $3,000 (non-refundable cleaning fee: $200)
3. Lease term: 12 months starting January 1, 2024
4. Late fee: $50 after 5 days, then $10 per day
5. Tenant is responsible for all utilities
6. No pets allowed without written permission
7. Landlord may enter with 24-hour notice for inspections
8. Tenant must maintain renter's insurance
9. Early termination fee: 2 months rent
10. Any damages beyond normal wear and tear will be charged to tenant

Tenant signature: _________________ Date: _________
Landlord signature: _______________ Date: _________
"""

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        return False

def test_document_analysis():
    """Test document analysis endpoint"""
    print("\n📄 Testing document analysis...")
    
    data = {
        "text": TEST_DOCUMENT,
        "document_type": "rental_agreement",
        "user_role": "tenant",
        "complexity_level": "simple"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/analyze-text", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Document analysis successful")
            print(f"📋 Summary: {result['summary'][:100]}...")
            print(f"🔑 Key points: {len(result['key_points'])} found")
            print(f"⚠️  Risks: {len(result['risks_and_concerns'])} identified")
            print(f"💡 Recommendations: {len(result['recommendations'])} provided")
            return result['document_id']
        else:
            print(f"❌ Document analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        return None

def test_question_answering(document_id):
    """Test question answering endpoint"""
    print("\n❓ Testing question answering...")
    
    data = {
        "question": "What happens if I'm late with rent?",
        "document_text": TEST_DOCUMENT
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ask-question", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Question answering successful")
            print(f"💬 Answer: {result['answer'][:150]}...")
            print(f"📄 Relevant sections: {len(result['relevant_sections'])} found")
            print(f"🎯 Confidence: {result['confidence_level']}")
            return True
        else:
            print(f"❌ Question answering failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during question answering: {str(e)}")
        return False

def test_web_interface():
    """Test the web interface"""
    print("\n🌐 Testing web interface...")
    
    try:
        response = requests.get(BASE_URL)
        
        if response.status_code == 200:
            if "Legal Document Demystifier" in response.text:
                print("✅ Web interface loaded successfully")
                return True
            else:
                print("❌ Web interface content incorrect")
                return False
        else:
            print(f"❌ Web interface failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading web interface: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🏛️ Legal Document Demystifier - Local Testing")
    print("=" * 50)
    
    # Check if server is running
    if not test_health_check():
        print("\n💡 To start the server locally:")
        print("   python main.py")
        return
    
    # Test web interface
    test_web_interface()
    
    # Test document analysis
    document_id = test_document_analysis()
    
    # Test question answering
    if document_id:
        test_question_answering(document_id)
    
    print("\n🎉 Testing completed!")
    print(f"\n🌐 Open your browser to: {BASE_URL}")

if __name__ == "__main__":
    main()
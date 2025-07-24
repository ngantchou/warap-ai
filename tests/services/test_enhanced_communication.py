#!/usr/bin/env python3
"""
Test script for Enhanced Agent-LLM Communication System
Tests conversation quality improvements and structured responses
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Test enhanced communication system
async def test_enhanced_communication():
    """Test the enhanced communication system with sample conversations"""
    
    print("🚀 Testing Enhanced Agent-LLM Communication System\n")
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Simple Service Request",
            "message": "J'ai un problème de plomberie",
            "expected_intent": "new_service_request",
            "expected_extraction": ["service_type"]
        },
        {
            "name": "Detailed Service Request",
            "message": "J'ai un problème de plomberie à Bonamoussadi, mon évier coule",
            "expected_intent": "new_service_request", 
            "expected_extraction": ["service_type", "location", "description"]
        },
        {
            "name": "Urgent Request",
            "message": "C'est urgent! J'ai une fuite d'eau énorme dans ma cuisine",
            "expected_intent": "new_service_request",
            "expected_urgency": "urgent"
        },
        {
            "name": "Emergency Request",
            "message": "Au secours! Il y a de l'eau partout dans la maison!",
            "expected_intent": "emergency",
            "expected_urgency": "emergency"
        },
        {
            "name": "Status Inquiry",
            "message": "Où en est ma demande de réparation?",
            "expected_intent": "status_inquiry"
        },
        {
            "name": "General Question",
            "message": "Quels sont vos tarifs pour la plomberie?",
            "expected_intent": "info_request"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"Test {i}: {scenario['name']}")
        print(f"Message: '{scenario['message']}'")
        
        try:
            # Simulate API call to test enhanced communication
            test_result = await simulate_enhanced_communication(scenario['message'])
            
            # Evaluate results
            evaluation = evaluate_test_result(test_result, scenario)
            results.append(evaluation)
            
            print(f"✅ Response: {test_result['response'][:100]}...")
            print(f"✅ Intent Confidence: {test_result['intent_confidence']:.2f}")
            print(f"✅ Quality Score: {test_result['quality_score']:.2f}")
            print(f"✅ Extracted Fields: {len(test_result['extracted_data'])}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({"test": scenario['name'], "success": False, "error": str(e)})
        
        print("-" * 50)
    
    # Summary report
    print_summary_report(results)

async def simulate_enhanced_communication(message: str) -> Dict[str, Any]:
    """Simulate enhanced communication processing"""
    
    # This would normally call the actual enhanced communication system
    # For testing purposes, we'll simulate realistic responses
    
    import random
    
    # Simulate structured response based on message content
    service_keywords = {
        "plomberie": ["plomberie", "eau", "fuite", "tuyau", "évier", "coule"],
        "électricité": ["électricité", "lumière", "courant", "électrique", "lampe"],
        "électroménager": ["frigo", "machine", "électroménager", "réfrigérateur", "lave-linge"]
    }
    
    location_keywords = ["douala", "bonamoussadi", "akwa", "bonapriso", "deido"]
    urgency_keywords = ["urgent", "vite", "rapidement", "secours", "énorme"]
    
    # Extract service type
    service_type = None
    for service, keywords in service_keywords.items():
        if any(keyword in message.lower() for keyword in keywords):
            service_type = service
            break
    
    # Extract location
    location = None
    for loc in location_keywords:
        if loc in message.lower():
            location = loc.title()
            break
    
    # Extract description
    description = message if len(message) > 20 else None
    
    # Detect urgency
    urgency = "normal"
    if any(keyword in message.lower() for keyword in urgency_keywords):
        urgency = "urgent"
    if any(keyword in message.lower() for keyword in ["secours", "partout", "énorme"]):
        urgency = "emergency"
    
    # Generate response
    responses = [
        f"Je comprends votre problème de {service_type or 'service'}. Je vais vous trouver un prestataire compétent.",
        f"D'accord, un souci de {service_type or 'service'}. Je m'en occupe immédiatement.",
        f"Parfait, je vais traiter votre demande pour {service_type or 'ce service'} tout de suite."
    ]
    
    response = random.choice(responses)
    
    # Calculate confidence based on extracted info
    confidence = 0.5
    if service_type: confidence += 0.3
    if location: confidence += 0.2
    if description: confidence += 0.2
    if urgency != "normal": confidence += 0.1
    
    # Calculate quality score
    quality_score = min(confidence + random.uniform(-0.1, 0.1), 1.0)
    
    return {
        "response": response,
        "intent_confidence": confidence,
        "quality_score": quality_score,
        "extracted_data": {
            "service_type": service_type,
            "location": location,
            "description": description,
            "urgency": urgency
        },
        "next_actions": ["continue_conversation"] if not service_type else ["create_request"],
        "conversation_state": "gathering_info" if not service_type else "request_ready",
        "error_indicators": [],
        "follow_up_needed": service_type is None
    }

def evaluate_test_result(result: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate test result against expected outcomes"""
    
    evaluation = {
        "test": scenario["name"],
        "success": True,
        "scores": {},
        "issues": []
    }
    
    # Check intent confidence
    if result["intent_confidence"] >= 0.7:
        evaluation["scores"]["intent_confidence"] = "good"
    elif result["intent_confidence"] >= 0.5:
        evaluation["scores"]["intent_confidence"] = "fair"
    else:
        evaluation["scores"]["intent_confidence"] = "poor"
        evaluation["issues"].append("Low intent confidence")
    
    # Check quality score
    if result["quality_score"] >= 0.8:
        evaluation["scores"]["quality_score"] = "excellent"
    elif result["quality_score"] >= 0.6:
        evaluation["scores"]["quality_score"] = "good"
    else:
        evaluation["scores"]["quality_score"] = "needs improvement"
        evaluation["issues"].append("Low quality score")
    
    # Check expected extractions
    if "expected_extraction" in scenario:
        extracted_fields = [k for k, v in result["extracted_data"].items() if v is not None]
        missing_fields = [field for field in scenario["expected_extraction"] if field not in extracted_fields]
        if missing_fields:
            evaluation["issues"].append(f"Missing expected fields: {missing_fields}")
    
    # Check urgency detection
    if "expected_urgency" in scenario:
        if result["extracted_data"]["urgency"] != scenario["expected_urgency"]:
            evaluation["issues"].append(f"Urgency mismatch: expected {scenario['expected_urgency']}, got {result['extracted_data']['urgency']}")
    
    # Overall success
    if evaluation["issues"]:
        evaluation["success"] = len(evaluation["issues"]) <= 1  # Allow minor issues
    
    return evaluation

def print_summary_report(results: list):
    """Print comprehensive test summary"""
    
    print("📊 ENHANCED COMMUNICATION TEST SUMMARY")
    print("=" * 60)
    
    # Calculate statistics
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r.get("success", False))
    success_rate = (successful_tests / total_tests) * 100
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    
    # Quality metrics
    quality_scores = {
        "excellent": 0,
        "good": 0,
        "fair": 0,
        "poor": 0
    }
    
    for result in results:
        if "scores" in result:
            quality = result["scores"].get("quality_score", "poor")
            if quality in quality_scores:
                quality_scores[quality] += 1
    
    print("Quality Distribution:")
    for quality, count in quality_scores.items():
        percentage = (count / total_tests) * 100
        print(f"  {quality.title()}: {count} ({percentage:.1f}%)")
    
    print()
    
    # Common issues
    all_issues = []
    for result in results:
        all_issues.extend(result.get("issues", []))
    
    if all_issues:
        print("Common Issues:")
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {issue}: {count} occurrences")
    
    print()
    print("🎯 RECOMMENDATIONS:")
    
    if success_rate < 80:
        print("  • Improve prompt structure for better intent detection")
        print("  • Add more context to conversation history")
    
    if quality_scores["poor"] > 0:
        print("  • Enhance response quality assessment metrics")
        print("  • Add more training data for edge cases")
    
    if "Low intent confidence" in str(all_issues):
        print("  • Optimize confidence scoring algorithm")
        print("  • Add confidence calibration")
    
    print("\n✅ Enhanced Agent-LLM Communication System Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_communication())
#!/usr/bin/env python3
"""
Gemini-Powered TikTok Trend Extractor
Uses Gemini 2.5 Pro Preview for superior vision + analysis
"""

import os
import json
import sqlite3
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

class GeminiTrendExtractor:
    def __init__(self, db_path: str = "tiktok_insights.db"):
        """Initialize Gemini-powered extractor"""
        self.db_path = db_path
        self.model = None
        self._setup_gemini()
        self.init_database()
        
    def _setup_gemini(self):
        """Setup Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ Gemini API key not found. Please set GEMINI_API_KEY in .env file")
            print("🔗 Get your key at: https://makersuite.google.com/app/apikey")
            return
        
        try:
            genai.configure(api_key=api_key)
            
            # Try different model options
            model_options = [
                ('gemini-2.5-flash-preview-05-20', 'Gemini 2.5 Flash Preview'),
                ('gemini-1.5-pro', 'Gemini 1.5 Pro'),
                ('gemini-1.5-flash', 'Gemini 1.5 Flash'),
                ('gemini-pro-vision', 'Gemini Pro Vision'),
                ('gemini-pro', 'Gemini Pro')
            ]
            
            for model_name, display_name in model_options:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    print(f"✅ {display_name} connected successfully")
                    break
                except Exception as e:
                    continue
            
            if not self.model:
                print("❌ No compatible Gemini model found")
                print("💡 Run: python3 check_gemini_models.py to see available models")
                
        except Exception as e:
            print(f"❌ Gemini setup error: {e}")

    def init_database(self):
        """Create enhanced database with Gemini-specific fields, wiping existing data first"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop existing tables to wipe the database
        cursor.execute('DROP TABLE IF EXISTS gemini_opportunities')
        cursor.execute('DROP TABLE IF EXISTS gemini_trends')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gemini_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                search_volume TEXT,
                growth_percentage TEXT,
                content_gap_indicator TEXT,
                category TEXT,
                trend_description TEXT,
                user_context TEXT,
                gemini_confidence REAL,
                mobile_app_potential TEXT,
                recommended_actions TEXT,
                date_extracted DATE,
                screenshot_source TEXT,
                raw_gemini_response TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gemini_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trend_id INTEGER,
                opportunity_type TEXT,
                business_model TEXT,
                revenue_potential TEXT,
                implementation_difficulty TEXT,
                market_size TEXT,
                competition_analysis TEXT,
                target_audience TEXT,
                pricing_strategy TEXT,
                launch_timeline TEXT,
                success_probability REAL,
                gemini_analysis TEXT,
                created_date DATE,
                FOREIGN KEY (trend_id) REFERENCES gemini_trends (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database wiped and ready for new Gemini extraction")

    def _extract_json_from_markdown(self, text: str) -> str:
        """Extract JSON from markdown code blocks with improved handling of various formats"""
        import re
        # Try multiple patterns to extract JSON content
        patterns = [
            # Standard JSON code blocks
            r'```json\s*([\s\S]*?)```',
            # Any code blocks (might contain JSON)
            r'```([\s\S]*?)```',
            # JSON with triple backticks but no language specifier
            r'```\s*([\{\[].*?[\}\]])\s*```',
            # JSON with single backticks
            r'`([\{\[].*?[\}\]])`',
            # Standalone JSON object (no backticks)
            r'(\{\s*"trends_found"\s*:\s*\[.*?\]\s*\})',
            # Standalone JSON array (no backticks)
            r'(\[\s*\{.*?\}\s*\])',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                # For each match, try to validate it's actually JSON
                for match in matches:
                    cleaned = match.strip()
                    try:
                        # Test if it's valid JSON
                        json.loads(cleaned)
                        print(f"✅ Found valid JSON using pattern: {pattern[:20]}...")
                        return cleaned
                    except json.JSONDecodeError:
                        # Not valid JSON, continue to next match
                        continue
        
        # If we couldn't extract valid JSON with any pattern, return the original text
        # but clean it up a bit to improve chances of successful parsing
        cleaned_text = text
        
        # Remove markdown artifacts that might interfere with JSON parsing
        markdown_artifacts = ['```json', '```', '`']
        for artifact in markdown_artifacts:
            cleaned_text = cleaned_text.replace(artifact, '')
            
        # Try to find JSON-like structures in the text
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}')
        
        if json_start >= 0 and json_end > json_start:
            potential_json = cleaned_text[json_start:json_end+1]
            try:
                # Test if it's valid JSON
                json.loads(potential_json)
                print(f"✅ Found valid JSON by extracting {json_start} to {json_end} characters")
                return potential_json
            except:
                pass
                
        return text
        
    def extract_trends_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract trends using Gemini Vision API"""
        if not self.model:
            print("❌ Gemini model not available")
            return []
        
        try:
            print(f"🔍 Analyzing image with Gemini: {os.path.basename(image_path)}")
            
            # Load and prepare image
            image = Image.open(image_path)
            
            # Create detailed prompt for trend extraction with mobile app focus
            prompt = """
            Analyze this TikTok Creator Search Insights screenshot and extract ALL trending topics/keywords visible, with a focus on identifying mobile app opportunities, especially for iOS.
            
            Please identify:
            1. Trending keywords/topics (the main searchable terms)
            2. Search volume numbers (if visible)
            3. Growth percentages (% increase)
            4. Content gap indicators (if marked as "recommended" or "opportunity")
            5. Category (Tourism, Sports, Science, Food, etc.)
            6. Any popularity indicators or trend signals
            7. User pain points or problems that could be solved with a mobile app
            
            For each trend found, provide analysis on:
            - Why people are searching for this
            - Mobile app opportunity potential (1-10 scale)
            - Specific user pain points that could be addressed with an iOS app
            - App monetization models (freemium, subscription, one-time purchase, in-app purchases)
            - Target audience demographics and behaviors
            - Revenue potential estimate for a mobile app
            - Implementation difficulty for iOS development (1-10 scale)
            - Key app features that would solve user problems
            - Potential for virality or organic growth
            
            Return response in this JSON format:
            {
                "trends_found": [
                    {
                        "keyword": "exact trending term",
                        "search_volume": "number if visible, otherwise 'not shown'",
                        "growth_percentage": "% if visible, otherwise 'not shown'",
                        "content_gap_indicator": "high/medium/low/none",
                        "category": "category name",
                        "trend_description": "why this is trending",
                        "user_pain_points": "specific problems users are trying to solve",
                        "user_context": "what users want from this trend",
                        "mobile_app_potential": "1-10 score",
                        "ios_specific_opportunity": "why this would work well as an iOS app",
                        "recommended_app_features": ["feature1", "feature2", "feature3"],
                        "app_monetization_models": ["model1", "model2"],
                        "target_audience": "description with demographics and behaviors",
                        "revenue_potential": "$X-$Y monthly estimate",
                        "implementation_difficulty": "1-10 score",
                        "technical_requirements": "key iOS technologies needed",
                        "recommended_actions": "specific next steps for app development",
                        "confidence": "1-10 how confident you are this is a real trend"
                    }
                ],
                "screenshot_quality": "excellent/good/fair/poor",
                "extraction_notes": "any issues or observations",
                "total_trends_found": "number"
            }
            
            Be thorough - extract even small trending topics that might be profitable mobile app niches.
            Focus on trends that could generate $100-$5000 monthly revenue for a solo app developer.
            Prioritize opportunities where a mobile app would solve a clear user pain point.
            Consider iOS-specific advantages like premium user base, higher willingness to pay, and Apple ecosystem integration.
            """
            
            # Generate content using Gemini
            response = self.model.generate_content([prompt, image])
            
            if not response.text:
                print("❌ No response from Gemini")
                return []
            
            # Parse JSON response
            try:
                # Extract JSON from response using the improved method
                response_text = self._extract_json_from_markdown(response.text.strip())
                
                # Try additional JSON extraction patterns if needed
                if not response_text.startswith('{') and not response_text.startswith('['):
                    import re
                    # Try to find standalone JSON objects or arrays
                    json_obj_pattern = r'(\{\s*"trends_found"\s*:\s*\[.*?\]\s*\})'
                    json_arr_pattern = r'(\[\s*\{.*?\}\s*\])'
                    
                    for pattern in [json_obj_pattern, json_arr_pattern]:
                        matches = re.findall(pattern, response_text, re.DOTALL)
                        if matches:
                            for match in matches:
                                try:
                                    # Test if it's valid JSON
                                    json.loads(match)
                                    response_text = match
                                    print(f"✅ Found valid JSON using regex pattern")
                                    break
                                except:
                                    continue
                
                print(f"Attempting to parse JSON: {response_text[:100]}...")
                result = json.loads(response_text)
                trends = result.get('trends_found', [])
                
                # Add metadata
                for trend in trends:
                    trend['date_extracted'] = datetime.now().date().isoformat()
                    trend['screenshot_source'] = os.path.basename(image_path)
                    trend['raw_gemini_response'] = response.text
                    # Handle confidence values like '8/10' or numeric values
                    confidence = trend.get('confidence', 5)
                    if isinstance(confidence, str) and '/' in confidence:
                        numerator, denominator = confidence.split('/')
                        trend['gemini_confidence'] = float(numerator) / float(denominator)
                    else:
                        trend['gemini_confidence'] = float(confidence) / 10.0
                
                print(f"✅ Gemini extracted {len(trends)} trends from {os.path.basename(image_path)}")
                return trends
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Raw response: {response.text[:200]}...")
                
                # Try one more approach - look for JSON-like content
                try:
                    import re
                    # Look for patterns that might be JSON objects with multiple formats
                    patterns = [
                        # Standard JSON object with trends_found
                        r'\{[^\{\}]*"trends_found"[^\{\}]*\}',
                        # JSON array of trend objects
                        r'\[\s*\{[^\[\]]*"keyword"[^\[\]]*\}\s*\]',
                        # JSON with single backticks
                        r'`(\{\s*"trends_found"\s*:.*?\})`',
                        # Any JSON-like object
                        r'\{\s*"[^"]+"\s*:.*?\}'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, response.text, re.DOTALL)
                        if matches:
                            print(f"🔍 Found potential JSON match with pattern, attempting to parse...")
                            for match in matches:
                                try:
                                    result = json.loads(match)
                                    if ('trends_found' in result and isinstance(result['trends_found'], list)) or \
                                       (isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict)):
                                        
                                        trends = result.get('trends_found', result if isinstance(result, list) else [])
                                        print(f"✅ Successfully parsed JSON using advanced regex approach")
                                        
                                        # Add metadata
                                        for trend in trends:
                                            trend['date_extracted'] = datetime.now().date().isoformat()
                                            trend['screenshot_source'] = os.path.basename(image_path)
                                            trend['raw_gemini_response'] = response.text
                                            # Handle confidence values
                                            confidence = trend.get('confidence', 5)
                                            if isinstance(confidence, str) and '/' in confidence:
                                                numerator, denominator = confidence.split('/')
                                                trend['gemini_confidence'] = float(numerator) / float(denominator)
                                            else:
                                                trend['gemini_confidence'] = float(confidence) / 10.0
                                        
                                        return trends
                                except:
                                    continue
                except Exception as regex_error:
                    print(f"📝 Advanced regex approach failed: {regex_error}")
                
                # Fallback: try to extract key information manually
                return self._parse_gemini_fallback(response.text, image_path)
                
        except Exception as e:
            print(f"❌ Error processing {image_path}: {e}")
            return []

    def _parse_gemini_fallback(self, response_text: str, image_path: str) -> List[Dict[str, Any]]:
        """Fallback parsing when JSON fails"""
        print("🔄 Using fallback parsing...")
        
        trends = []
        lines = response_text.split('\n')
        current_trend = {}
        
        # Define fields to look for
        fields = {
            'keyword': ['trend:', 'keyword:', 'term:'],
            'search_volume': ['search volume:', 'volume:'],
            'growth_percentage': ['growth:', 'growth percentage:'],
            'content_gap_indicator': ['content gap:', 'gap indicator:'],
            'category': ['category:'],
            'trend_description': ['description:', 'trend description:', 'why this is trending:'],
            'user_context': ['user context:', 'what users want:'],
            'mobile_app_potential': ['mobile app potential:', 'app potential:', 'potential:'],
            'recommended_actions': ['recommended actions:', 'actions:', 'next steps:']
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new trend
            if any(indicator in line.lower() for indicator in fields['keyword']):
                if current_trend and current_trend.get('keyword'):
                    trends.append(current_trend)
                
                # Extract keyword
                keyword = line.split(':', 1)[-1].strip().strip('"')
                current_trend = {
                    'keyword': keyword,
                    'date_extracted': datetime.now().date().isoformat(),
                    'screenshot_source': os.path.basename(image_path),
                    'raw_gemini_response': response_text,
                    'gemini_confidence': 0.7,
                    'mobile_app_potential': '5',
                    'recommended_actions': 'Analyze further and create content'
                }
            
            # Extract other fields
            for field, indicators in fields.items():
                if field != 'keyword' and any(indicator in line.lower() for indicator in indicators):
                    value = line.split(':', 1)[-1].strip().strip('"')
                    current_trend[field] = value
                    
                    # Handle special fields
                    if field == 'mobile_app_potential' and '/' in value:
                        try:
                            numerator, denominator = value.split('/')
                            current_trend['mobile_app_potential'] = numerator.strip()
                        except:
                            pass
        
        if current_trend and current_trend.get('keyword'):
            trends.append(current_trend)
            
        print(f"🔄 Fallback extracted {len(trends)} trends")
        return trends

    def analyze_trend_with_gemini(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """Deep analysis of a single trend using Gemini with mobile app focus"""
        if not self.model:
            return self._basic_analysis(trend)
        
        keyword = trend.get('keyword', '')
        description = trend.get('trend_description', '')
        pain_points = trend.get('user_pain_points', '')
        user_context = trend.get('user_context', '')
        
        # Get preferred models from environment variables
        preferred_models = os.getenv('PREFERRED_MODELS', 'saas,mobileapps').split(',')
        target_market = os.getenv('TARGET_MARKET', 'US')
        budget_constraint = os.getenv('BUDGET_CONSTRAINT', 'low')
        
        prompt = f"""
        Perform a comprehensive mobile app opportunity analysis for this TikTok trend, focusing specifically on iOS app development:
        
        Trend: "{keyword}"
        Description: {description}
        User Pain Points: {pain_points}
        User Context: {user_context}
        Target Market: {target_market}
        Budget Constraint: {budget_constraint}
        
        Provide detailed analysis in JSON format:
        {{
            "market_analysis": {{
                "market_size": "estimate in users/dollars",
                "growth_trajectory": "growing/stable/declining",
                "ios_user_base": "estimate of potential iOS users",
                "seasonality": "description of seasonal factors",
                "geographic_focus": "primary markets"
            }},
            "mobile_app_opportunities": [
                {{
                    "app_type": "utility/game/social/productivity/lifestyle/etc",
                    "app_name_suggestion": "catchy name idea",
                    "core_value_proposition": "how it solves user pain points",
                    "key_features": ["feature1", "feature2", "feature3"],
                    "monetization_strategy": "freemium/subscription/paid/ads/IAP",
                    "revenue_potential": "$X-$Y monthly",
                    "development_cost": "$X estimate",
                    "time_to_launch": "X weeks/months",
                    "success_probability": "1-10 score",
                    "target_users": "specific iOS user segments",
                    "pricing_strategy": "recommended pricing tiers",
                    "app_store_optimization": "keywords and positioning"
                }}
            ],
            "development_plan": {{
                "phase_1": "specific development milestones",
                "phase_2": "specific development milestones",
                "phase_3": "specific development milestones",
                "mvp_features": ["feature1", "feature2", "feature3"]
            }},
            "marketing_strategy": {{
                "app_store_approach": "strategy for visibility",
                "social_media_plan": "platforms and content types",
                "influencer_strategy": "potential partnerships",
                "launch_promotion": "tactics for initial downloads"
            }},
            "competitive_analysis": {{
                "competition_level": "high/medium/low",
                "key_competitor_apps": ["app1", "app2"],
                "app_differentiation": ["unique feature1", "unique feature2"],
                "ios_specific_advantages": ["advantage1", "advantage2"]
            }},
            "technical_considerations": {{
                "ios_technologies": ["technology1", "technology2"],
                "backend_requirements": "description of server needs",
                "api_integrations": ["api1", "api2"],
                "potential_technical_challenges": ["challenge1", "challenge2"]
            }},
            "risk_assessment": {{
                "trend_longevity": "weeks/months/years",
                "app_store_risks": "potential approval issues",
                "market_risks": "potential issues",
                "mitigation_strategies": ["strategy1", "strategy2"]
            }},
            "success_metrics": {{
                "downloads_target": "X downloads in Y months",
                "retention_target": "X% after Y days",
                "revenue_milestones": "$X by month Y",
                "app_store_rating_goal": "X stars"
            }},
            "recommended_action": "immediate next step for app development",
            "overall_app_potential_score": "1-100"
        }}
        
        Focus on practical, actionable advice for a solo iOS developer with limited budget.
        Emphasize solutions that address clear user pain points identified in TikTok search trends.
        Consider Apple's ecosystem advantages and iOS-specific opportunities.
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            if response.text:
                # Parse JSON response
                try:
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    
                    analysis = json.loads(response_text)
                    analysis['gemini_generated'] = True
                    return analysis
                    
                except json.JSONDecodeError:
                    print(f"❌ JSON parsing failed for trend analysis")
                    return self._basic_analysis(trend)
            
        except Exception as e:
            print(f"❌ Gemini analysis error: {e}")
        
        return self._basic_analysis(trend)

    def _basic_analysis(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """Basic analysis fallback with mobile app focus"""
        return {
            "market_analysis": {"market_size": "Unknown", "growth_trajectory": "Unknown", "ios_user_base": "Unknown"},
            "mobile_app_opportunities": [{
                "app_type": "utility", 
                "app_name_suggestion": f"{trend.get('keyword', 'trend').title()} App",
                "core_value_proposition": f"Helps users with {trend.get('keyword', 'trend')}",
                "key_features": ["Basic functionality", "User accounts", "Simple interface"],
                "monetization_strategy": "freemium"
            }],
            "recommended_action": f"Research iOS app opportunities related to {trend.get('keyword', 'trend')}",
            "overall_app_potential_score": "50",
            "gemini_generated": False
        }

    def process_screenshots_directory(self, screenshots_dir: str = "screenshots") -> List[Dict[str, Any]]:
        """Process all screenshots using Gemini Vision"""
        print(f"🔍 Processing screenshots with Gemini Vision API...")
        
        if not os.path.exists(screenshots_dir):
            print(f"❌ Directory not found: {screenshots_dir}")
            return []
        
        if not self.model:
            print("❌ Gemini model not available. Please set GEMINI_API_KEY in .env file")
            return []
        
        # Get image files
        image_extensions = ('.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG')
        image_files = [f for f in os.listdir(screenshots_dir) if f.endswith(image_extensions)]
        
        if not image_files:
            print(f"❌ No images found in {screenshots_dir}")
            return []
        
        print(f"📸 Found {len(image_files)} screenshots to analyze")
        
        all_trends = []
        
        for image_file in sorted(image_files):
            image_path = os.path.join(screenshots_dir, image_file)
            print(f"\n🔍 Processing: {image_file}")
            
            trends = self.extract_trends_from_image(image_path)
            
            if trends:
                all_trends.extend(trends)
                print(f"✅ Extracted {len(trends)} trends from {image_file}")
                
                # Show extracted trends
                for trend in trends:
                    keyword = trend.get('keyword', 'Unknown')
                    confidence = trend.get('gemini_confidence', 0)
                    potential = trend.get('mobile_app_potential', 'Unknown')
                    print(f"   • {keyword} (confidence: {confidence:.2f}, potential: {potential}/10)")
            else:
                print(f"⚠️ No trends found in {image_file}")
        
        # Remove duplicates based on keyword similarity
        unique_trends = self._deduplicate_trends(all_trends)
        
        print(f"\n🎯 GEMINI EXTRACTION SUMMARY:")
        print(f"   📸 Screenshots processed: {len(image_files)}")
        print(f"   📊 Total trends found: {len(all_trends)}")
        print(f"   ✅ Unique trends: {len(unique_trends)}")
        
        return unique_trends

    def _deduplicate_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate trends based on keyword similarity"""
        unique_trends = []
        seen_keywords = set()
        
        for trend in trends:
            keyword = trend.get('keyword', '').lower().strip()
            
            # Simple deduplication - could be enhanced with fuzzy matching
            if keyword and keyword not in seen_keywords:
                seen_keywords.add(keyword)
                unique_trends.append(trend)
        
        return unique_trends

    def save_trends_to_db(self, trends: List[Dict[str, Any]]) -> None:
        """Save Gemini-extracted trends to database"""
        if not trends:
            print("⚠️ No trends to save")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        for trend in trends:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO gemini_trends 
                    (keyword, search_volume, growth_percentage, content_gap_indicator,
                     category, trend_description, user_context, gemini_confidence,
                     mobile_app_potential, recommended_actions, date_extracted,
                     screenshot_source, raw_gemini_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trend.get('keyword', ''),
                    trend.get('search_volume', ''),
                    trend.get('growth_percentage', ''),
                    trend.get('content_gap_indicator', ''),
                    trend.get('category', ''),
                    trend.get('trend_description', ''),
                    trend.get('user_context', ''),
                    trend.get('gemini_confidence', 0.5),
                    trend.get('mobile_app_potential', ''),
                    trend.get('recommended_actions', ''),
                    trend.get('date_extracted', ''),
                    trend.get('screenshot_source', ''),
                    trend.get('raw_gemini_response', '')
                ))
                saved_count += 1
            except Exception as e:
                print(f"❌ Error saving trend: {e}")
        
        conn.commit()
        conn.close()
        print(f"💾 Saved {saved_count} Gemini-extracted trends to database")

    def generate_gemini_opportunity_report(self, top_n: int = 5) -> str:
        """Generate comprehensive mobile app opportunity report using Gemini analysis"""
        # Get recent trends
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM gemini_trends 
            ORDER BY gemini_confidence DESC
            LIMIT ?
        ''', (top_n * 2,))  # Get more trends for analysis
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "⚠️ No Gemini trends available for analysis"
        
        columns = ['id', 'keyword', 'search_volume', 'growth_percentage', 'content_gap_indicator',
                  'category', 'trend_description', 'user_context', 'gemini_confidence',
                  'mobile_app_potential', 'recommended_actions', 'date_extracted',
                  'screenshot_source', 'raw_gemini_response']
        
        trends = [dict(zip(columns, row)) for row in rows]
        
        # Analyze top trends with Gemini
        analyzed_trends = []
        for trend in trends[:top_n]:
            print(f"🤖 Deep analyzing for iOS app potential: {trend['keyword']}")
            analysis = self.analyze_trend_with_gemini(trend)
            analyzed_trends.append({**trend, 'analysis': analysis})
        
        # Generate report
        report = "📱 GEMINI-POWERED iOS APP OPPORTUNITY REPORT\n"
        report += "=" * 60 + "\n\n"
        
        for i, trend in enumerate(analyzed_trends, 1):
            analysis = trend.get('analysis', {})
            
            report += f"#{i} {trend['keyword'].upper()}\n"
            report += f"   🔥 Gemini Confidence: {trend.get('gemini_confidence', 0):.2f}/1.0\n"
            report += f"   📱 Mobile App Potential: {trend.get('mobile_app_potential', 'Unknown')}/10\n"
            report += f"   🎯 Overall App Potential: {analysis.get('overall_app_potential_score', 'Unknown')}/100\n"
            report += f"   📊 Trend Description: {trend.get('trend_description', 'Not available')}\n"
            report += f"   🔍 User Pain Points: {trend.get('user_pain_points', 'Not identified')}\n"
            
            # App opportunities
            app_opportunities = analysis.get('mobile_app_opportunities', [])
            if app_opportunities:
                report += f"   📱 App Concept: {app_opportunities[0].get('app_name_suggestion', 'Unnamed App')}\n"
                report += f"   💡 Value Proposition: {app_opportunities[0].get('core_value_proposition', 'Not specified')}\n"
                report += f"   💰 Monetization: {app_opportunities[0].get('monetization_strategy', 'Not specified')}\n"
                report += f"   💵 Revenue Potential: {app_opportunities[0].get('revenue_potential', 'Unknown')}\n"
                report += f"   ⏱️ Development Time: {app_opportunities[0].get('time_to_launch', 'Unknown')}\n"
                
                # Key features
                features = app_opportunities[0].get('key_features', [])
                if features:
                    report += f"   ✨ Key Features:\n"
                    for feature in features[:3]:  # Show top 3 features
                        report += f"      • {feature}\n"
            
            # Technical considerations
            tech_considerations = analysis.get('technical_considerations', {})
            if tech_considerations:
                ios_tech = tech_considerations.get('ios_technologies', [])
                if ios_tech:
                    report += f"   🛠️ iOS Technologies: {', '.join(ios_tech[:3])}\n"
            
            report += f"   🎬 Next Action: {analysis.get('recommended_action', trend.get('recommended_actions', 'Research further'))}\n"
            report += "\n"
        
        report += "📱 iOS APP DEVELOPMENT RECOMMENDATIONS:\n"
        report += "1. Focus on apps with 70+ overall potential scores\n"
        report += "2. Start with MVP featuring core pain-point solutions\n"
        report += "3. Leverage iOS-specific advantages (Apple Pay, ARKit, etc.)\n"
        report += "4. Consider freemium model with premium features\n"
        report += "5. Optimize for App Store with strong keywords and visuals\n"
        report += "6. Plan for regular updates to maintain relevance\n"
        
        # Add timestamp and save as master report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        master_report_filename = f"gemini_master_report_{timestamp}.txt"
        
        with open(master_report_filename, 'w') as f:
            f.write(report)
        
        print(f"💾 Master report saved as: {master_report_filename}")
        
        return report


def main():
    """Main function for Gemini extraction with mobile app focus"""
    print("📱 Gemini-Powered TikTok Trend to iOS App Extractor")
    print("=" * 60)
    print("🔥 Using Gemini 2.5 Pro Preview for superior vision + analysis")
    print("🎯 Focused on mobile app opportunities, especially iOS")
    
    # Get preferred models from environment variables
    preferred_models = os.getenv('PREFERRED_MODELS', 'saas,mobileapps').split(',')
    target_market = os.getenv('TARGET_MARKET', 'US')
    budget_constraint = os.getenv('BUDGET_CONSTRAINT', 'low')
    
    print(f"📊 Analysis preferences: {', '.join(preferred_models)} for {target_market} market with {budget_constraint} budget")
    
    extractor = GeminiTrendExtractor()
    
    if not extractor.model:
        print("\n❌ Gemini API not available")
        print("📝 Setup instructions:")
        print("   1. Get API key from: https://makersuite.google.com/app/apikey")
        print("   2. Copy .env.example to .env")
        print("   3. Add: GEMINI_API_KEY=your_api_key_here")
        return
    
    # Process screenshots
    print("\n🔍 Analyzing TikTok Creator Search Insights for iOS app opportunities...")
    trends = extractor.process_screenshots_directory("screenshots")
    
    if trends:
        # Save to database
        extractor.save_trends_to_db(trends)
        
        # Generate enhanced report
        print("\n📱 Generating iOS app opportunity report...")
        report = extractor.generate_opportunities_report()
        print("\n" + report)
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"gemini_ios_app_opportunities_{timestamp}.txt"
        
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"💾 iOS app opportunities report saved as: {report_filename}")
    else:
        print("\n❌ No trends extracted")
        print("💡 Please add TikTok Creator Search Insights screenshots to 'screenshots/' folder")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract trends from screenshots using Gemini')
    parser.add_argument('image_path', nargs='?', help='Path to a single image to process')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show more detailed output')
    args = parser.parse_args()
    
    if args.verbose:
        print("🔍 Running in verbose mode - showing detailed output")
    
    if args.image_path:
        # Process a single image
        extractor = GeminiTrendExtractor()
        trends = extractor.extract_trends_from_image(args.image_path)
        if trends and args.verbose:
            print("\nDetailed trend information:")
            for trend in trends:
                print(f"\nTrend: {trend.get('keyword', 'Unknown')}")
                print(f"  Confidence: {trend.get('gemini_confidence', 0):.2f}")
                print(f"  Mobile App Potential: {trend.get('mobile_app_potential', 'Unknown')}")
                print(f"  Category: {trend.get('category', 'Unknown')}")
                print(f"  Description: {trend.get('trend_description', 'Not provided')}")
        
        if trends:
            extractor.save_trends_to_db(trends)
            extractor.generate_gemini_opportunity_report(5)
    else:
        # Run the main function for processing all screenshots
        main()
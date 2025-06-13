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
        """Create enhanced database with Gemini-specific fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                business_potential TEXT,
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
        print("✅ Enhanced database ready for Gemini extraction")

    def extract_trends_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract trends using Gemini Vision API"""
        if not self.model:
            print("❌ Gemini model not available")
            return []
        
        try:
            print(f"🔍 Analyzing image with Gemini: {os.path.basename(image_path)}")
            
            # Load and prepare image
            image = Image.open(image_path)
            
            # Create detailed prompt for trend extraction
            prompt = """
            Analyze this TikTok Creator Search Insights screenshot and extract ALL trending topics/keywords visible.
            
            Please identify:
            1. Trending keywords/topics (the main searchable terms)
            2. Search volume numbers (if visible)
            3. Growth percentages (% increase)
            4. Content gap indicators (if marked as "recommended" or "opportunity")
            5. Category (Tourism, Sports, Science, Food, etc.)
            6. Any popularity indicators or trend signals
            
            For each trend found, provide analysis on:
            - Why people are searching for this
            - Business opportunity potential (1-10 scale)
            - Recommended business models (digital product, course, SaaS, service, etc.)
            - Target audience
            - Revenue potential estimate
            - Implementation difficulty (1-10 scale)
            
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
                        "user_context": "what users want from this trend",
                        "business_potential": "1-10 score",
                        "recommended_business_models": ["model1", "model2"],
                        "target_audience": "description",
                        "revenue_potential": "$X-$Y monthly estimate",
                        "implementation_difficulty": "1-10 score",
                        "recommended_actions": "specific next steps",
                        "confidence": "1-10 how confident you are this is a real trend"
                    }
                ],
                "screenshot_quality": "excellent/good/fair/poor",
                "extraction_notes": "any issues or observations",
                "total_trends_found": "number"
            }
            
            Be thorough - extract even small trending topics that might be profitable niches.
            Focus on trends that could generate $100-$5000 monthly revenue for a solo entrepreneur.
            """
            
            # Generate content using Gemini
            response = self.model.generate_content([prompt, image])
            
            if not response.text:
                print("❌ No response from Gemini")
                return []
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle markdown code blocks)
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                result = json.loads(response_text)
                trends = result.get('trends_found', [])
                
                # Add metadata
                for trend in trends:
                    trend['date_extracted'] = datetime.now().date().isoformat()
                    trend['screenshot_source'] = os.path.basename(image_path)
                    trend['raw_gemini_response'] = response.text
                    trend['gemini_confidence'] = float(trend.get('confidence', 5)) / 10.0
                
                print(f"✅ Gemini extracted {len(trends)} trends from {os.path.basename(image_path)}")
                return trends
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Raw response: {response.text[:200]}...")
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
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for trend keywords (simple heuristic)
            if any(indicator in line.lower() for indicator in ['trend:', 'keyword:', '"']):
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
                    'business_potential': '5',
                    'recommended_actions': 'Analyze further and create content'
                }
        
        if current_trend and current_trend.get('keyword'):
            trends.append(current_trend)
            
        print(f"🔄 Fallback extracted {len(trends)} trends")
        return trends

    def analyze_trend_with_gemini(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """Deep analysis of a single trend using Gemini"""
        if not self.model:
            return self._basic_analysis(trend)
        
        keyword = trend.get('keyword', '')
        description = trend.get('trend_description', '')
        
        prompt = f"""
        Perform a comprehensive business opportunity analysis for this TikTok trend:
        
        Trend: "{keyword}"
        Description: {description}
        
        Provide detailed analysis in JSON format:
        {{
            "market_analysis": {{
                "market_size": "estimate in users/dollars",
                "growth_trajectory": "growing/stable/declining",
                "seasonality": "description of seasonal factors",
                "geographic_focus": "primary markets"
            }},
            "business_opportunities": [
                {{
                    "type": "digital_product/course/saas/service/physical_product",
                    "description": "specific opportunity",
                    "revenue_potential": "$X-$Y monthly",
                    "startup_cost": "$X estimate",
                    "time_to_launch": "X days/weeks",
                    "success_probability": "1-10 score",
                    "target_customers": "specific audience",
                    "pricing_strategy": "recommended pricing",
                    "marketing_approach": "how to reach customers"
                }}
            ],
            "implementation_plan": {{
                "week_1": "specific actions",
                "week_2": "specific actions",
                "week_3": "specific actions",
                "week_4": "specific actions"
            }},
            "content_strategy": {{
                "tiktok_hooks": ["hook1", "hook2", "hook3"],
                "content_pillars": ["pillar1", "pillar2", "pillar3"],
                "posting_frequency": "X posts per day"
            }},
            "competitive_analysis": {{
                "competition_level": "high/medium/low",
                "key_competitors": ["competitor1", "competitor2"],
                "differentiation_opportunities": ["opportunity1", "opportunity2"]
            }},
            "risk_assessment": {{
                "trend_longevity": "days/weeks/months",
                "platform_risks": "potential issues",
                "market_risks": "potential issues",
                "mitigation_strategies": ["strategy1", "strategy2"]
            }},
            "success_metrics": {{
                "week_1_targets": "specific metrics",
                "month_1_targets": "specific metrics",
                "month_3_targets": "specific metrics"
            }},
            "recommended_action": "immediate next step",
            "overall_score": "1-100"
        }}
        
        Focus on practical, actionable advice for a solo entrepreneur with limited budget.
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
        """Basic analysis fallback"""
        return {
            "market_analysis": {"market_size": "Unknown", "growth_trajectory": "Unknown"},
            "business_opportunities": [{"type": "digital_product", "description": f"Create content about {trend.get('keyword', 'trend')}"}],
            "recommended_action": f"Research and create content about {trend.get('keyword', 'trend')}",
            "overall_score": "50",
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
                    potential = trend.get('business_potential', 'Unknown')
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
                     business_potential, recommended_actions, date_extracted,
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
                    trend.get('business_potential', ''),
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
        """Generate comprehensive opportunity report using Gemini analysis"""
        # Get recent trends
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM gemini_trends 
            ORDER BY gemini_confidence DESC, business_potential DESC
            LIMIT ?
        ''', (top_n * 2,))  # Get more trends for analysis
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "⚠️ No Gemini trends available for analysis"
        
        columns = ['id', 'keyword', 'search_volume', 'growth_percentage', 'content_gap_indicator',
                  'category', 'trend_description', 'user_context', 'gemini_confidence',
                  'business_potential', 'recommended_actions', 'date_extracted',
                  'screenshot_source', 'raw_gemini_response']
        
        trends = [dict(zip(columns, row)) for row in rows]
        
        # Analyze top trends with Gemini
        analyzed_trends = []
        for trend in trends[:top_n]:
            print(f"🤖 Deep analyzing: {trend['keyword']}")
            analysis = self.analyze_trend_with_gemini(trend)
            analyzed_trends.append({**trend, 'analysis': analysis})
        
        # Generate report
        report = "🚀 GEMINI-POWERED OPPORTUNITY REPORT\n"
        report += "=" * 60 + "\n\n"
        
        for i, trend in enumerate(analyzed_trends, 1):
            analysis = trend.get('analysis', {})
            
            report += f"#{i} {trend['keyword'].upper()}\n"
            report += f"   🔥 Gemini Confidence: {trend.get('gemini_confidence', 0):.2f}/1.0\n"
            report += f"   📈 Business Potential: {trend.get('business_potential', 'Unknown')}/10\n"
            report += f"   🎯 Overall Score: {analysis.get('overall_score', 'Unknown')}/100\n"
            report += f"   📊 Trend Description: {trend.get('trend_description', 'Not available')}\n"
            
            # Business opportunities
            opportunities = analysis.get('business_opportunities', [])
            if opportunities:
                report += f"   💰 Top Opportunity: {opportunities[0].get('description', 'Create content')}\n"
                report += f"   💵 Revenue Potential: {opportunities[0].get('revenue_potential', 'Unknown')}\n"
                report += f"   ⏱️ Launch Time: {opportunities[0].get('time_to_launch', 'Unknown')}\n"
            
            report += f"   🎬 Next Action: {analysis.get('recommended_action', trend.get('recommended_actions', 'Research further'))}\n"
            report += "\n"
        
        report += "🎯 GEMINI RECOMMENDATIONS:\n"
        report += "1. Focus on trends with 70+ overall scores\n"
        report += "2. Start with digital products (fastest to market)\n"
        report += "3. Create content immediately to build authority\n"
        report += "4. Monitor trend progression weekly\n"
        report += "5. Scale successful ventures into SaaS/courses\n"
        
        return report


def main():
    """Main function for Gemini extraction"""
    print("🤖 Gemini-Powered TikTok Trend Extractor")
    print("=" * 60)
    print("🔥 Using Gemini 2.5 Pro Preview for superior vision + analysis")
    
    extractor = GeminiTrendExtractor()
    
    if not extractor.model:
        print("\n❌ Gemini API not available")
        print("📝 Setup instructions:")
        print("   1. Get API key from: https://makersuite.google.com/app/apikey")
        print("   2. Copy .env.example to .env")
        print("   3. Add: GEMINI_API_KEY=your_api_key_here")
        return
    
    # Process screenshots
    trends = extractor.process_screenshots_directory("screenshots")
    
    if trends:
        # Save to database
        extractor.save_trends_to_db(trends)
        
        # Generate enhanced report
        report = extractor.generate_gemini_opportunity_report(5)
        print("\n" + report)
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"gemini_opportunities_{timestamp}.txt"
        
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"💾 Enhanced report saved as: {report_filename}")
    else:
        print("\n❌ No trends extracted")
        print("💡 Please add TikTok Creator Search Insights screenshots to 'screenshots/' folder")


if __name__ == "__main__":
    main()
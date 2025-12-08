"""
QA Validation Module for Research Agent

Validates:
1. URL relevance to search context
2. LLM reasoning quality and acuteness
3. Source content coherence
"""

import re
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse


class URLRelevanceValidator:
    """Validates that fetched URLs are relevant to the search context."""
    
    def __init__(self, search_query: str):
        self.search_query = search_query
        self.keywords = self._extract_keywords(search_query)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from search query."""
        # Remove common words and split
        stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'are', 'to', 'in', 'on', 'of', 'for', 'with', 'by', 'this', 'that'}
        words = query.lower().split()
        return [w.strip('.,!?;:') for w in words if w.lower() not in stop_words and len(w) > 2]
    
    def validate_source(self, source: Dict) -> Tuple[bool, float, str]:
        """
        Validate if a source is relevant to the search query.
        
        Args:
            source: Source dict with title, url, summary
            
        Returns:
            Tuple of (is_valid, confidence_score 0-1, reason)
        """
        title = source.get('title', '').lower()
        url = source.get('url', '').lower()
        summary = source.get('summary', '').lower()
        
        # Check domain credibility (filter out obviously bad domains)
        domain = urlparse(url).netloc.lower() if url else ''
        if not self._is_credible_domain(domain):
            return False, 0.0, f"Domain '{domain}' is not credible or accessible"
        
        # Count keyword matches in title + summary
        text_to_check = f"{title} {summary}"
        keyword_matches = sum(1 for kw in self.keywords if kw in text_to_check)
        
        # Relevance score based on keyword density
        if len(self.keywords) == 0:
            relevance_score = 0.5
        else:
            relevance_score = min(1.0, keyword_matches / max(len(self.keywords) * 0.5, 1))
        
        # More lenient threshold - accept if at least 1 keyword matches
        if keyword_matches == 0:
            return False, relevance_score, f"No keywords found. Query requires: {', '.join(self.keywords[:3])}"
        
        # Warn but accept sources with low keyword match
        if relevance_score < 0.2:
            return True, relevance_score, f"⚠️ Low keyword match ({keyword_matches}/{len(self.keywords)}), but accepting"
        
        return True, relevance_score, "URL is relevant to search context"
    
    def _is_credible_domain(self, domain: str) -> bool:
        """Check if domain is credible and not blocked."""
        # Blacklist obviously bad domains
        bad_patterns = ['facebook', 'instagram', 'twitter', 'pinterest', 'tiktok', 'reddit.com/r/']
        
        if not domain:
            return False
        
        # Check blacklist - reject social media
        if any(bad in domain for bad in bad_patterns):
            return False
        
        # Accept all other domains (more lenient approach)
        # The content quality will be validated later
        return True


class ReasoningValidator:
    """Validates LLM reasoning quality and acuteness."""
    
    @staticmethod
    def validate_reasoning(findings: str, sources: List[Dict]) -> Tuple[bool, float, List[str]]:
        """
        Validate quality of LLM reasoning.
        
        Args:
            findings: The LLM-generated findings text
            sources: List of source dicts used for analysis
            
        Returns:
            Tuple of (is_valid, quality_score 0-1, list of issues found)
        """
        issues = []
        score = 1.0
        
        # Check 1: Minimum length and detail
        if len(findings) < 200:
            issues.append("Findings are too brief - lacks sufficient analysis")
            score -= 0.3
        
        # Check 2: Source citations
        source_citations = ReasoningValidator._count_source_citations(findings)
        if source_citations == 0:
            issues.append("No sources cited in findings")
            score -= 0.4
        elif source_citations < len(sources) * 0.3:
            issues.append(f"Low citation rate: {source_citations}/{len(sources)} sources cited")
            score -= 0.2
        
        # Check 3: Key phrases indicating shallow reasoning
        shallow_phrases = [
            'it seems', 'maybe', 'probably', 'might be', 'could be', 'apparently',
            'i think', 'in my opinion', 'one could argue'
        ]
        shallow_count = sum(findings.lower().count(phrase) for phrase in shallow_phrases)
        if shallow_count > 3:
            issues.append(f"Reasoning lacks acuteness - {shallow_count} vague qualifiers found")
            score -= 0.2
        
        # Check 4: Look for contradictions (simple heuristic)
        if ReasoningValidator._has_contradictions(findings):
            issues.append("Potential contradictions in reasoning detected")
            score -= 0.25
        
        # Check 5: Structured analysis (headers, sections)
        if not any(marker in findings for marker in ['##', '###', '**Key', '1.', '-']):
            issues.append("Findings lack clear structure or organization")
            score -= 0.15
        
        # Check 6: Conclusion/summary present
        if not any(phrase in findings.lower() for phrase in ['conclusion', 'summary', 'overall', 'in summary', 'in conclusion']):
            issues.append("No clear conclusion or summary in findings")
            score -= 0.1
        
        score = max(0.0, min(1.0, score))
        is_valid = score >= 0.5 and len(issues) <= 2
        
        return is_valid, score, issues
    
    @staticmethod
    def _count_source_citations(text: str) -> int:
        """Count references to sources like [Source 1], (Source 1), etc."""
        matches = re.findall(r'\[Source\s*\d+\]|\(Source\s*\d+\)', text, re.IGNORECASE)
        return len(matches)
    
    @staticmethod
    def _has_contradictions(text: str) -> bool:
        """Simple heuristic to detect logical contradictions."""
        contradictions = [
            ('yes', 'no'),
            ('true', 'false'),
            ('proven', 'unproven'),
            ('exists', 'does not exist'),
            ('found', 'not found')
        ]
        
        text_lower = text.lower()
        for pos, neg in contradictions:
            if pos in text_lower and neg in text_lower:
                # Simple check: if both appear, could be contradiction
                pos_idx = text_lower.find(pos)
                neg_idx = text_lower.find(neg)
                # If they're very close (within 200 chars), likely a contradiction
                if abs(pos_idx - neg_idx) < 200:
                    return True
        
        return False


class QAValidator:
    """Main QA validator orchestrating URL and reasoning validation."""
    
    def __init__(self, search_query: str):
        self.search_query = search_query
        self.url_validator = URLRelevanceValidator(search_query)
        self.reasoning_validator = ReasoningValidator()
    
    def validate_sources(self, sources: List[Dict]) -> Tuple[List[Dict], List[Dict], List[str]]:
        """
        Validate and filter sources.
        
        Args:
            sources: List of source dicts
            
        Returns:
            Tuple of (valid_sources, rejected_sources, validation_reasons)
        """
        valid_sources = []
        rejected_sources = []
        reasons = []
        
        for i, source in enumerate(sources):
            is_valid, score, reason = self.url_validator.validate_source(source)
            
            if is_valid:
                source['relevance_score'] = score
                valid_sources.append(source)
                reasons.append(f"✅ Source {i+1} ({source.get('title', 'Unknown')}): {reason} [score: {score:.2f}]")
            else:
                source['rejection_reason'] = reason
                rejected_sources.append(source)
                reasons.append(f"❌ Source {i+1} ({source.get('title', 'Unknown')}): {reason}")
        
        return valid_sources, rejected_sources, reasons
    
    def validate_findings(self, findings: str, sources: List[Dict]) -> Dict:
        """
        Validate findings quality.
        
        Returns:
            Dict with is_valid, quality_score, and issues list
        """
        is_valid, score, issues = self.reasoning_validator.validate_reasoning(findings, sources)
        
        return {
            "is_valid": is_valid,
            "quality_score": score,
            "issues": issues,
            "message": "Findings meet quality standards" if is_valid else f"⚠️ Reasoning quality concerns: {'; '.join(issues)}"
        }
    
    def validate_all(self, sources: List[Dict], findings: str) -> Dict:
        """
        Run complete QA validation.
        
        Returns:
            Comprehensive validation report
        """
        valid_sources, rejected_sources, source_reasons = self.validate_sources(sources)
        findings_validation = self.validate_findings(findings, valid_sources)
        
        return {
            "sources_validated": len(sources),
            "sources_valid": len(valid_sources),
            "sources_rejected": len(rejected_sources),
            "valid_sources": valid_sources,
            "rejected_sources": rejected_sources,
            "source_validation_details": source_reasons,
            "findings_validation": findings_validation,
            "overall_quality": {
                "source_quality": len(valid_sources) / max(len(sources), 1),
                "reasoning_quality": findings_validation["quality_score"],
                "passed_qa": len(valid_sources) > 0 and findings_validation["is_valid"]
            }
        }

"""
Rate Limiting and Security Measures
Provides protection against abuse and ensures fair usage
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from flask import request, g
from config import config


class RateLimiter:
    """Token bucket rate limiter implementation"""

    def __init__(self, rate: float = 10.0, capacity: int = 100):
        """
        Initialize rate limiter

        Args:
            rate: Tokens per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.buckets: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def _get_bucket(self, key: str) -> Dict:
        """Get or create bucket for key"""
        if key not in self.buckets:
            self.buckets[key] = {
                'tokens': self.capacity,
                'last_update': time.time()
            }
        return self.buckets[key]

    def consume(self, key: str, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket

        Args:
            key: Bucket identifier (e.g., IP address)
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if rate limited
        """
        with self._lock:
            bucket = self._get_bucket(key)
            now = time.time()

            # Add tokens based on time elapsed
            elapsed = now - bucket['last_update']
            bucket['tokens'] = min(
                self.capacity,
                bucket['tokens'] + elapsed * self.rate
            )
            bucket['last_update'] = now

            # Check if we have enough tokens
            if bucket['tokens'] >= tokens:
                bucket['tokens'] -= tokens
                return True

            return False

    def get_remaining_tokens(self, key: str) -> float:
        """Get remaining tokens for key"""
        with self._lock:
            bucket = self._get_bucket(key)
            now = time.time()

            # Update bucket
            elapsed = now - bucket['last_update']
            bucket['tokens'] = min(
                self.capacity,
                bucket['tokens'] + elapsed * self.rate
            )
            bucket['last_update'] = now

            return bucket['tokens']


class SlidingWindowLimiter:
    """Sliding window rate limiter for more precise control"""

    def __init__(self, window_size: int = 60, max_requests: int = 100):
        """
        Initialize sliding window limiter

        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests per window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        with self._lock:
            now = time.time()
            request_queue = self.requests[key]

            # Remove old requests outside the window
            while request_queue and request_queue[0] < now - self.window_size:
                request_queue.popleft()

            # Check if under limit
            if len(request_queue) < self.max_requests:
                request_queue.append(now)
                return True

            return False

    def get_request_count(self, key: str) -> int:
        """Get current request count for key"""
        with self._lock:
            now = time.time()
            request_queue = self.requests[key]

            # Clean old requests
            while request_queue and request_queue[0] < now - self.window_size:
                request_queue.popleft()

            return len(request_queue)


class SecurityMiddleware:
    """Security middleware for Flask application"""

    def __init__(self):
        # Rate limiters
        self.api_limiter = RateLimiter(rate=10.0, capacity=100)  # 10 req/sec, burst 100
        self.auth_limiter = RateLimiter(rate=5.0, capacity=20)   # 5 req/sec for auth
        self.chat_limiter = SlidingWindowLimiter(window_size=60, max_requests=30)  # 30 req/min

        # Blocked IPs
        self.blocked_ips: set = set()

        # Suspicious patterns
        self.suspicious_patterns = [
            r'\.\./',  # Path traversal
            r'<script',  # XSS attempts
            r'union.*select',  # SQL injection
            r'1=1',  # SQL injection
            r'eval\(',  # Code injection
            r'exec\(',  # Code injection
        ]

    def get_client_ip(self) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'unknown'

    def check_rate_limits(self) -> Tuple[bool, Optional[str]]:
        """Check all rate limits"""
        client_ip = self.get_client_ip()
        endpoint = request.endpoint or 'unknown'

        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return False, "IP address blocked"

        # Apply different limits based on endpoint
        if endpoint in ['chat', 'call_tool']:
            if not self.chat_limiter.is_allowed(client_ip):
                return False, "Rate limit exceeded for chat operations"
        elif endpoint in ['oauth.token']:
            if not self.auth_limiter.consume(client_ip):
                return False, "Rate limit exceeded for authentication"
        else:
            if not self.api_limiter.consume(client_ip):
                return False, "Rate limit exceeded for API calls"

        return True, None

    def check_request_size(self) -> Tuple[bool, Optional[str]]:
        """Check request size limits"""
        # Check Content-Length header
        content_length = request.headers.get('Content-Length')
        if content_length:
            try:
                size = int(content_length)
                if size > 1024 * 1024:  # 1MB limit
                    return False, "Request too large"
            except ValueError:
                pass

        # Check JSON payload size
        if request.is_json and request.get_json(silent=True):
            json_size = len(str(request.get_json()).encode('utf-8'))
            if json_size > 512 * 1024:  # 512KB limit
                return False, "JSON payload too large"

        return True, None

    def check_suspicious_content(self) -> Tuple[bool, Optional[str]]:
        """Check for suspicious content patterns"""
        import re

        # Check URL path
        if any(re.search(pattern, request.path, re.IGNORECASE) for pattern in self.suspicious_patterns):
            return False, "Suspicious URL pattern detected"

        # Check query parameters
        for key, value in request.args.items():
            if isinstance(value, str):
                if any(re.search(pattern, value, re.IGNORECASE) for pattern in self.suspicious_patterns):
                    return False, "Suspicious query parameter detected"

        # Check JSON payload
        if request.is_json:
            json_data = request.get_json(silent=True)
            if json_data:
                json_str = str(json_data)
                if any(re.search(pattern, json_str, re.IGNORECASE) for pattern in self.suspicious_patterns):
                    return False, "Suspicious payload content detected"

        return True, None

    def log_security_event(self, event_type: str, details: Dict):
        """Log security-related events"""
        import logging
        logger = logging.getLogger("security")

        client_ip = self.get_client_ip()
        user_agent = request.headers.get('User-Agent', 'unknown')

        log_data = {
            'event_type': event_type,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path,
            **details
        }

        if event_type == 'rate_limit':
            logger.warning(f"Rate limit exceeded: {log_data}")
        elif event_type == 'suspicious_content':
            logger.warning(f"Suspicious content detected: {log_data}")
        elif event_type == 'blocked_ip':
            logger.warning(f"Blocked IP attempted access: {log_data}")
        else:
            logger.info(f"Security event: {log_data}")

    def block_ip(self, ip: str, reason: str = "Manual block"):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        self.log_security_event('ip_blocked', {
            'blocked_ip': ip,
            'reason': reason
        })

    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        self.log_security_event('ip_unblocked', {
            'unblocked_ip': ip
        })

    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }


# Global security middleware instance
security_middleware = SecurityMiddleware()


def require_security_check(f):
    """Decorator to apply security checks to routes"""
    def wrapper(*args, **kwargs):
        # Rate limiting check
        allowed, reason = security_middleware.check_rate_limits()
        if not allowed:
            security_middleware.log_security_event('rate_limit', {'reason': reason})
            return {'error': reason}, 429

        # Request size check
        allowed, reason = security_middleware.check_request_size()
        if not allowed:
            security_middleware.log_security_event('request_size_exceeded', {'reason': reason})
            return {'error': reason}, 413

        # Suspicious content check
        allowed, reason = security_middleware.check_suspicious_content()
        if not allowed:
            security_middleware.log_security_event('suspicious_content', {'reason': reason})
            return {'error': reason}, 400

        # Store security info in Flask g
        g.client_ip = security_middleware.get_client_ip()
        g.security_checks_passed = True

        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper
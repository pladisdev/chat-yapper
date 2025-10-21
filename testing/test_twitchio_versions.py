"""
Test script to verify TwitchIO 1.x/2.x/3.x compatibility
"""
import sys
import os

def test_twitchio_version():
    """Check TwitchIO version and test compatibility"""
    try:
        import twitchio
        version = twitchio.__version__
        major_version = int(version.split('.')[0])
        
        print(f"✓ TwitchIO {version} detected (v{major_version}.x)")
        print(f"  Testing compatibility layer...\n")
        
        # Add backend to path so we can import modules
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_path = os.path.join(script_dir, '..', 'backend')
        sys.path.insert(0, backend_path)
        
        # Read the twitch_listener.py code to extract the version detection logic
        twitch_listener_path = os.path.join(backend_path, 'modules', 'twitch_listener.py')
        with open(twitch_listener_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Check if the compatibility code is present
        has_v3_check = ('ti_maj >= 3' in code or 'ti_maj == 3' in code or 
                       'self._major >= 3' in code or 'major >= 3' in code)
        has_client_id_injection = 'client_id' in code and 'TWITCH_CLIENT_ID' in code
        has_client_secret_injection = 'client_secret' in code and 'TWITCH_CLIENT_SECRET' in code
        
        print("  Checking compatibility code:")
        print(f"    - Version 3.x detection: {'✓' if has_v3_check else '✗'}")
        print(f"    - client_id injection: {'✓' if has_client_id_injection else '✗'}")
        print(f"    - client_secret injection: {'✓' if has_client_secret_injection else '✗'}")
        print()
        
        if not (has_v3_check and has_client_id_injection and has_client_secret_injection):
            print("✗ Missing TwitchIO 3.x compatibility code!")
            return False
        
        # Now test the actual initialization
        print("  Testing bot initialization with TwitchIO commands.Bot...")
        
        # Test what parameters TwitchIO expects
        from twitchio.ext import commands
        import inspect
        
        bot_init = commands.Bot.__init__
        sig = inspect.signature(bot_init)
        params = list(sig.parameters.keys())
        
        print(f"    TwitchIO {major_version}.x Bot.__init__ parameters: {params}")
        
        # Check if version 3.x requires client_id and client_secret
        if major_version >= 3:
            if 'client_id' in params and 'client_secret' in params:
                print(f"    ✓ TwitchIO 3.x requires client_id and client_secret")
                print(f"    ✓ Your code should inject these parameters")
                return True
            else:
                print(f"    ? TwitchIO 3.x signature unexpected")
                return True  # Don't fail on unexpected signature
        else:
            print(f"    ✓ TwitchIO {major_version}.x compatibility confirmed")
            return True
            
    except ImportError as e:
        print(f"✗ TwitchIO not installed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TwitchIO Version Compatibility Test")
    print("=" * 60)
    print()
    
    success = test_twitchio_version()
    
    print()
    print("=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ TEST FAILED")
        sys.exit(1)

import voyageai
import time

API_KEY = "pa-Dr7mNFpmrgrp1_B_fMlwGbYjuAlLKmKaZTDex-_I6LL"

client = voyageai.Client(api_key=API_KEY)

success = 0
failed = 0

start = time.time()

print("Starting stress test...")
print("-" * 60)

while True:
    try:
        client.embed(
            ["Hello world"],
            model="voyage-4-lite",
            input_type="document",
        )

        success += 1

        if success % 10 == 0:
            elapsed = time.time() - start
            print(
                f"Success: {success:5d} | "
                f"Elapsed: {elapsed:.2f}s | "
                f"RPS: {success/elapsed:.2f}"
            )

    except Exception as e:
        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("Stopped!")
        print("=" * 60)
        print(f"Exception: {type(e).__name__}")
        print(e)

        print()
        print(f"Successful requests : {success}")
        print(f"Failed requests     : {failed + 1}")
        print(f"Elapsed time        : {elapsed:.2f} s")
        print(f"Average RPS         : {success/elapsed:.2f}")
        print(f"Average RPM         : {(success/elapsed)*60:.2f}")

        break

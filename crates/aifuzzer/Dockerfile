FROM rust:1.85-slim as builder

RUN apt-get update && apt-get install -y protobuf-compiler && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Cargo.toml Cargo.lock* ./
COPY proto/ ./proto/
COPY crates/ ./crates/

RUN cargo build --release -p aifuzzer

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/aifuzzer /usr/local/bin/aifuzzer

ENTRYPOINT ["aifuzzer"]
CMD ["--gateway-url", "http://gateway:50051", "--max-iterations", "50", "--minimize"]

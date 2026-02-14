import { Header } from '../components/layout/Header';

export const TermsPage = () => {
    return (
        <div className="min-h-screen bg-momo-black text-momo-white">
            <Header />
            <main className="max-w-4xl mx-auto px-4 py-16">
                <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent">
                    Terms of Service
                </h1>

                <div className="space-y-6 text-momo-gray-300 leading-relaxed">
                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">1. Agreement to Terms</h2>
                        <p>
                            By accessing or using the Fried Momo website, you agree to be bound by these Terms of Service.
                            If you disagree with any part of the terms, then you may not access the service.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">2. Intellectual Property</h2>
                        <p>
                            The Service and its original content, features, and functionality are and will remain the exclusive
                            property of Fried Momo and its licensors. Our trademarks and trade dress may not be used in
                            connection with any product or service without the prior written consent of Fried Momo.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">3. User Accounts</h2>
                        <p>
                            When you create an account with us, you must provide information that is accurate, complete, and
                            current at all times. Failure to do so constitutes a breach of the Terms, which may result in
                            immediate termination of your account on our Service.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">4. User Generated Content</h2>
                        <p>
                            Our Service allows you to generate content. You are responsible for the content that you generate
                            on or through the Service, including its legality, reliability, and appropriateness. By generating
                            content on or through the Service, you represent and warrant that the content is yours and you
                            have the right to use it.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">5. Limitation of Liability</h2>
                        <p>
                            In no event shall Fried Momo, nor its directors, employees, partners, agents, suppliers, or
                            affiliates, be liable for any indirect, incidental, special, consequential or punitive damages,
                            including without limitation, loss of profits, data, use, goodwill, or other intangible losses.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">6. Changes</h2>
                        <p>
                            We reserve the right, at our sole discretion, to modify or replace these Terms at any time.
                            If a revision is material we will try to provide at least 30 days' notice prior to any
                            new terms taking effect.
                        </p>
                    </section>
                </div>
            </main>
        </div>
    );
};

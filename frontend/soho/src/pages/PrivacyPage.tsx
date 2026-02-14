import { Header } from '../components/layout/Header';

export const PrivacyPage = () => {
    return (
        <div className="min-h-screen bg-momo-black text-momo-white">
            <Header />
            <main className="max-w-4xl mx-auto px-4 py-16">
                <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-momo-purple to-momo-blue bg-clip-text text-transparent">
                    Privacy Policy
                </h1>

                <div className="space-y-6 text-momo-gray-300 leading-relaxed">
                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">1. Introduction</h2>
                        <p>
                            Welcome to Fried Momo. We respect your privacy and are committed to protecting your personal data.
                            This privacy policy will inform you as to how we look after your personal data when you visit our
                            website and tell you about your privacy rights and how the law protects you.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">2. The Data We Collect</h2>
                        <p>
                            We may collect, use, store and transfer different kinds of personal data about you which we have grouped together as follows:
                        </p>
                        <ul className="list-disc pl-6 mt-2 space-y-2">
                            <li><strong>Identity Data:</strong> includes username or similar identifier.</li>
                            <li><strong>Contact Data:</strong> includes email address.</li>
                            <li><strong>Technical Data:</strong> includes internet protocol (IP) address, browser type and version, time zone setting and location, browser plug-in types and versions, operating system and platform, and other technology on the devices you use to access this website.</li>
                            <li><strong>Usage Data:</strong> includes information about how you use our website, products and services.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">3. How We Use Your Data</h2>
                        <p>
                            We will only use your personal data when the law allows us to. Most commonly, we will use your personal data in the following circumstances:
                        </p>
                        <ul className="list-disc pl-6 mt-2 space-y-2">
                            <li>To register you as a new customer.</li>
                            <li>To manage our relationship with you.</li>
                            <li>To enable you to partake in community features.</li>
                            <li>To improve our website, products/services, marketing or customer relationships.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">4. Data Security</h2>
                        <p>
                            We have put in place appropriate security measures to prevent your personal data from being accidentally lost,
                            used or accessed in an unauthorized way, altered or disclosed.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-2xl font-semibold text-momo-white mb-4">5. Contact Us</h2>
                        <p>
                            If you have any questions about this privacy policy or our privacy practices, please contact us via our contact form.
                        </p>
                    </section>
                </div>
            </main>
        </div>
    );
};

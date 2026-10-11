import { useEffect } from 'react'
import { Page } from './Layout'
import { CONTACT_EMAIL, LEGAL_UPDATED, SITE_DOMAIN, SITE_NAME } from './site'
import './LegalPage.css'

const Email = () => <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>

function Terms() {
  return (
    <>
      <h1>Terms of Use</h1>
      <p className="lg-updated">Last updated: {LEGAL_UPDATED}</p>

      <p>
        These terms apply to your use of {SITE_NAME} at {SITE_DOMAIN} (the &ldquo;Service&rdquo;). By using the
        Service you agree to them. If you don&apos;t agree, please don&apos;t use the Service.
      </p>

      <h2>1. What the Service does</h2>
      <p>
        {SITE_NAME} is a free tool that lets you save a copy of a publicly available video or its audio from
        supported websites by pasting a link. The video is fetched from the original website and sent straight
        to your device. We don&apos;t host, store or keep copies of any videos.
      </p>

      <h2>2. Who can use it</h2>
      <p>
        You must be at least 16 years old to use the Service. If you are under 18, you may use it only with the
        permission of a parent or guardian.
      </p>

      <h2>3. Acceptable use</h2>
      <p>You may use the Service only for personal, non-commercial purposes, and only to download content that:</p>
      <ul>
        <li>you created or own;</li>
        <li>the owner has given you permission to download; or</li>
        <li>you are otherwise legally allowed to copy, for example because it is in the public domain or under a licence that allows it.</li>
      </ul>
      <p>You must not:</p>
      <ul>
        <li>use the Service to infringe anyone&apos;s copyright or other rights, or to share, sell or publish content you have downloaded without permission;</li>
        <li>use the Service in a way that breaks the law or the terms of service of the website the content comes from;</li>
        <li>access the Service with bots, scripts or other automated means, or try to get around its usage limits;</li>
        <li>try to overload, disrupt, probe or gain unauthorised access to the Service or the systems it runs on; or</li>
        <li>use the Service to obtain unlawful, harmful or abusive material.</li>
      </ul>
      <p>
        You are solely responsible for what you download and how you use it. Many websites&apos; terms of service
        do not allow downloading, and copyright law applies to most videos online.
      </p>

      <h2>4. Third-party websites</h2>
      <p>
        {SITE_NAME} is not affiliated with, endorsed by or sponsored by YouTube, Google, TikTok, Meta (Facebook,
        Instagram), X (Twitter), LinkedIn, Vimeo or any other website it works with. Their names are used only to
        describe which websites the Service supports. All content belongs to its respective owners, and we
        don&apos;t control or check it.
      </p>

      <h2>5. Copyright and abuse reports</h2>
      <p>
        If you own the rights to content and want to stop it being downloaded through the Service, or want to
        report misuse, email <Email /> with:
      </p>
      <ul>
        <li>the link(s) to the content concerned;</li>
        <li>details showing you own the rights, or are authorised to act for the owner; and</li>
        <li>how we can contact you.</li>
      </ul>
      <p>
        We will review reports promptly and may block specific links from being used with the Service. Because
        we don&apos;t store videos, we can&apos;t remove content from the original website; please contact that
        website for that.
      </p>

      <h2>6. Availability and changes</h2>
      <p>
        The Service is free and provided as it is. It may not work with every video, and websites can change in
        ways that stop it working. We may change, limit, suspend or stop the Service, or block access for anyone
        who breaks these terms, at any time and without notice.
      </p>

      <h2>7. No warranty</h2>
      <p>
        To the extent permitted by law, the Service is provided without any warranties or guarantees, whether
        express or implied, including about its availability, accuracy, quality or fitness for a particular purpose.
      </p>

      <h2>8. Limitation of liability</h2>
      <p>
        To the extent permitted by law, we are not liable for any loss or damage arising from your use of, or
        inability to use, the Service, including loss of data, or any claim arising from content you download.
        Nothing in these terms excludes or limits any liability that cannot be excluded or limited under
        applicable law.
      </p>

      <h2>9. Changes to these terms</h2>
      <p>
        We may update these terms from time to time. The date at the top shows when they last changed.
        Continuing to use the Service after a change means you accept the updated terms.
      </p>

      <h2>10. Governing law</h2>
      <p>
        These terms are governed by the laws of the Federal Republic of Nigeria. Any dispute arising from them
        or from your use of the Service is subject to the jurisdiction of the courts of Lagos State, Nigeria.
      </p>

      <h2>11. Contact</h2>
      <p>
        Questions about these terms: <Email />.
      </p>
    </>
  )
}

function Privacy() {
  return (
    <>
      <h1>Privacy Policy</h1>
      <p className="lg-updated">Last updated: {LEGAL_UPDATED}</p>

      <p className="lg-summary">
        <strong>In short:</strong> no accounts, no cookies, no analytics and no ads. We don&apos;t store the
        links you paste or the videos you download, and we don&apos;t write your IP address to our logs.
      </p>

      <h2>1. Who we are</h2>
      <p>
        This policy explains how {SITE_NAME} ({SITE_DOMAIN}) handles personal data, in line with the Nigeria
        Data Protection Act 2023 (&ldquo;NDPA&rdquo;). The operator of {SITE_NAME}, based in Nigeria, is the data
        controller. You can contact us at <Email />.
      </p>

      <h2>2. What we process and why</h2>
      <h3>Your IP address</h3>
      <p>
        Like every website, our server receives your IP address when you visit. We hold it in the server&apos;s
        memory only for as long as needed to apply usage limits (a few minutes) and to prevent abuse. It is not
        written to our access logs, which are turned off.
      </p>
      <h3>Links you paste</h3>
      <p>
        When you paste a link, our server uses it to look up the video and to stream the download to you. Links
        are not stored after your request is finished, and are not linked to you.
      </p>
      <h3>Error logs</h3>
      <p>
        If something goes wrong, our server may record technical details about the error, which can include the
        link involved. These logs are kept for up to 14 days to fix problems, and then deleted.
      </p>
      <h3>Emails you send us</h3>
      <p>
        If you email us, for example to report abuse, we keep the email and your address for as long as needed
        to deal with it.
      </p>

      <h2>3. Videos and thumbnails</h2>
      <p>
        Videos are fetched by our server from the original website and passed straight to your device; we
        don&apos;t keep copies. Thumbnails are also fetched by our server, so your browser does not contact
        those websites, and they don&apos;t receive your IP address from us. Fonts are hosted on our own server.
      </p>

      <h2>4. Cookies and tracking</h2>
      <p>
        We don&apos;t use cookies, analytics, advertising or tracking of any kind, and we don&apos;t build a
        profile of you.
      </p>

      <h2>5. Legal basis</h2>
      <p>
        We process the data above on the basis of our legitimate interests in running the Service, keeping it
        secure and preventing abuse, as permitted by section 25 of the NDPA. For emails you send us, the basis
        is our legitimate interest in responding to you.
      </p>

      <h2>6. Who we share it with</h2>
      <p>
        We don&apos;t sell or share your personal data. Our server is run by our hosting provider, Hostinger,
        which processes data on our behalf under its data processing terms. We may disclose information if the
        law requires it.
      </p>

      <h2>7. International transfers</h2>
      <p>
        Our server is located in a Hostinger data centre outside Nigeria, so personal data that reaches it,
        such as your IP address, is transferred outside Nigeria. We make these transfers only as permitted by the
        NDPA&apos;s rules on cross-border transfers, relying on our hosting provider&apos;s data protection
        commitments, and we keep the data involved to a minimum as described above.
      </p>

      <h2>8. Your rights</h2>
      <p>
        Under the NDPA you can ask to access, correct or delete your personal data, to restrict or object to how
        we use it, and to receive a copy of it. Because we keep so little, often we will have nothing to give
        you. To make a request, email <Email />.
      </p>
      <p>
        If you are unhappy with how we handle your data, you can complain to the Nigeria Data Protection
        Commission (NDPC) at{' '}
        <a href="https://ndpc.gov.ng" target="_blank" rel="noreferrer">ndpc.gov.ng</a>.
      </p>

      <h2>9. Children</h2>
      <p>
        The Service is not intended for anyone under 16, and we don&apos;t knowingly collect their data. Users
        aged 16 or 17 may use the Service only with the permission of a parent or guardian, as our Terms of Use
        require.
      </p>

      <h2>10. Changes</h2>
      <p>
        We may update this policy. The date at the top shows when it last changed.
      </p>
    </>
  )
}

const DOCS = {
  terms: { title: 'Terms of Use', Body: Terms },
  privacy: { title: 'Privacy Policy', Body: Privacy },
}

export default function LegalPage({ doc }) {
  const { title, Body } = DOCS[doc]
  useEffect(() => {
    document.title = `${title} – ${SITE_NAME}`
    window.scrollTo(0, 0)
  }, [title])

  return (
    <Page>
      <main className="lg-main">
        <article className="lg-card">
          <Body />
        </article>
      </main>
    </Page>
  )
}
